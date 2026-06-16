"""CT pseudo-label semi-supervised training (Method 2).

Loss per batch::

    L = L_hard + lambda * L_pseudo

where ``L_hard`` is weighted cross-entropy against the ground-truth X-ray
label on every sample, and ``L_pseudo`` is cross-entropy against the
trained CT teacher's argmax prediction on the subset of paired patients
where ``max(softmax(teacher_logits)) > tau_pseudo``. Samples below the
confidence threshold contribute no pseudo-label term — discarding noisy
teacher signal rather than softening it.

This differs from gated logit KD in three ways:
  1. The pseudo-label is the teacher's *one-hot argmax*, not a softened
     distribution, so the student is taught to match the teacher's
     decision rather than its calibrated soft distribution.
  2. The confidence filter is a hard mask (keep / drop) rather than a
     smooth per-sample weight in [0, 1].
  3. The hard-label CE branch always uses the true label; the teacher
     never overrides the ground-truth signal for confidently-classified
     samples — it only adds supervision on the same target shape.

The teacher is the matching ``{variant}_f{fold}_s{seed}_teacher`` Stage A
checkpoint (ResNet18 backbone, num_classes=2). Only the teacher's CT
representation is needed at training time; the student remains an X-ray-
only ResNet18Classifier and emits a plain ``best.pt`` state dict so the
held-out test split can be scored via the existing
``jdcnet_exp.evaluate`` entry point.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn, optim
from torch.utils.data import DataLoader

from .artifacts import (
    save_confusion_matrix,
    save_learning_curves,
    write_history_csv,
    write_json,
)
from .config import (
    DataConfig,
    DistillationConfig,
    ExperimentConfig,
    ModelConfig,
    OptimizationConfig,
)
from .data import create_dataloaders, load_filtered_manifests
from .metrics import compute_metrics
from .models import build_model


@dataclass
class PseudoLabelConfig:
    enabled: bool = True
    teacher_checkpoint: str = ""
    tau_pseudo: float = 0.70
    lambda_pseudo: float = 0.5
    soft: bool = False
    soft_temperature: float = 1.0
    # Calibration temperature applied to the teacher logits *before* computing the
    # confidence used by the gate mask (calibrate-then-gate). 1.0 reproduces the
    # original raw-confidence gate; T>1 softens (better-calibrated, fewer admitted);
    # T<1 sharpens (over-confident stress test). The argmax target is unaffected.
    teacher_temperature: float = 1.0


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _compute_class_weights(train_manifest, num_classes: int, device: torch.device) -> torch.Tensor:
    counts = (
        train_manifest["label"].value_counts().reindex(range(num_classes), fill_value=0).astype(float)
    )
    non_zero = counts.replace(0, np.nan)
    weights = counts.sum() / (len(counts) * non_zero)
    weights = weights.fillna(0.0)
    return torch.tensor(weights.to_numpy(), dtype=torch.float32, device=device)


def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, object]:
    model.eval()
    all_labels: list[int] = []
    all_probabilities: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            if len(batch) == 3:
                images, _paired, labels = batch
            else:
                images, labels = batch
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            logits = model(images)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()
            all_probabilities.append(probabilities)
            all_labels.extend(labels.cpu().tolist())
    stacked = np.concatenate(all_probabilities, axis=0)
    return compute_metrics(all_labels, stacked)


def _build_teacher(config: ExperimentConfig, checkpoint_path: Path, device: torch.device) -> nn.Module:
    teacher_cfg = ModelConfig(
        name="teacher",
        num_classes=config.model.num_classes,
        input_size=config.model.input_size,
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
        backbone=getattr(config.model, "backbone", "custom"),
    )
    teacher = build_model(teacher_cfg).to(device)
    state = torch.load(checkpoint_path, map_location=device)
    teacher.load_state_dict(state)
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    return teacher


def _load_config(config_path: str | Path) -> tuple[ExperimentConfig, PseudoLabelConfig]:
    with open(config_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    base = ExperimentConfig(
        experiment_name=payload["experiment_name"],
        manifest_path=payload["manifest_path"],
        output_dir=payload["output_dir"],
        seed=payload["seed"],
        model=ModelConfig(**payload["model"]),
        data=DataConfig(**payload["data"]),
        optimization=OptimizationConfig(**payload["optimization"]),
        distillation=DistillationConfig(**(payload.get("distillation") or {"enabled": False})),
    )
    pseudo_cfg = PseudoLabelConfig(**(payload.get("pseudo_label") or {}))
    return base, pseudo_cfg


def run_training(config_path: str | Path) -> None:
    config, pseudo_cfg = _load_config(config_path)
    if not pseudo_cfg.teacher_checkpoint:
        raise ValueError("pseudo_label.teacher_checkpoint must be set.")
    teacher_checkpoint = Path(pseudo_cfg.teacher_checkpoint)
    if not teacher_checkpoint.exists():
        raise FileNotFoundError(f"Teacher checkpoint not found: {teacher_checkpoint}")

    set_seed(config.seed)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = bool(config.optimization.amp and device.type == "cuda")

    train_loader, val_loader = create_dataloaders(config)
    train_manifest, _ = load_filtered_manifests(config)
    class_weights = _compute_class_weights(train_manifest, config.model.num_classes, device)

    student = build_model(config.model).to(device)
    teacher = _build_teacher(config, teacher_checkpoint, device)

    optimizer = optim.AdamW(
        student.parameters(),
        lr=config.optimization.learning_rate,
        weight_decay=config.optimization.weight_decay,
    )
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    best_score = -1.0
    history: list[dict[str, object]] = []
    pseudo_temp = max(pseudo_cfg.soft_temperature, 1e-3)
    gate_temp = max(float(getattr(pseudo_cfg, "teacher_temperature", 1.0)), 1e-3)
    tau = float(pseudo_cfg.tau_pseudo)
    lam = float(pseudo_cfg.lambda_pseudo)

    for epoch in range(1, config.optimization.epochs + 1):
        student.train()
        running_loss = 0.0
        running_pseudo_loss = 0.0
        kept = 0
        seen = 0

        for batch in train_loader:
            if len(batch) != 3:
                raise RuntimeError(
                    "Pseudo-label training requires paired (xray, ct, label) batches; "
                    "set data.paired_image_column on the manifest."
                )
            images, teacher_images, labels = batch
            images = images.to(device, non_blocking=True)
            teacher_images = teacher_images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)

            with torch.no_grad():
                teacher_logits = teacher(teacher_images)
                # Gate on calibrated confidence: scale logits by the calibration
                # temperature before the softmax used for masking. argmax (and thus
                # the hard pseudo-label) is invariant to this scaling; only which
                # samples clear the confidence threshold changes.
                gate_prob = torch.softmax(teacher_logits / gate_temp, dim=1)
                teacher_conf, teacher_pred = gate_prob.max(dim=1)
                mask = teacher_conf > tau

            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                logits = student(images)
                loss_hard = F.cross_entropy(logits, labels, weight=class_weights)
                if pseudo_cfg.soft:
                    soft_target = torch.softmax(teacher_logits / pseudo_temp, dim=1)
                    soft_log_student = F.log_softmax(logits / pseudo_temp, dim=1)
                    elementwise_kl = (soft_target * (soft_target.clamp_min(1e-12).log() - soft_log_student)).sum(dim=1)
                    if mask.any():
                        loss_pseudo = (elementwise_kl[mask].mean()) * (pseudo_temp ** 2)
                    else:
                        loss_pseudo = torch.zeros((), device=device, dtype=logits.dtype)
                else:
                    if mask.any():
                        loss_pseudo = F.cross_entropy(
                            logits[mask], teacher_pred[mask]
                        )
                    else:
                        loss_pseudo = torch.zeros((), device=device, dtype=logits.dtype)
                loss = loss_hard + lam * loss_pseudo

            if use_amp:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()

            running_loss += float(loss.item())
            running_pseudo_loss += float(loss_pseudo.detach().item())
            kept += int(mask.sum().item())
            seen += int(labels.numel())

        metrics: dict[str, object] = {
            "epoch": epoch,
            "train_loss": running_loss / max(len(train_loader), 1),
            "train_pseudo_loss": running_pseudo_loss / max(len(train_loader), 1),
            "pseudo_active_fraction": kept / max(seen, 1),
        }
        metrics.update(_evaluate(student, val_loader, device))
        score = float(metrics.get("balanced_accuracy", metrics["accuracy"]))
        if score > best_score:
            best_score = score
            torch.save(student.state_dict(), output_dir / "best.pt")
            write_json(metrics, output_dir / "best_metrics.json")
        history.append(metrics)
        print(
            f"[{config.experiment_name}] epoch={epoch} "
            f"loss={metrics['train_loss']:.4f} pseudo={metrics['train_pseudo_loss']:.4f} "
            f"keep={metrics['pseudo_active_fraction']:.2f} ba={metrics.get('balanced_accuracy', 'NaN')}"
        )

    write_json(history, output_dir / "history.json")
    write_history_csv(history, output_dir / "history.csv")
    save_learning_curves(history, output_dir / "learning_curves.png")

    student.load_state_dict(torch.load(output_dir / "best.pt", map_location=device))
    best_metrics = _evaluate(student, val_loader, device)
    write_json(best_metrics, output_dir / "best_metrics.json")
    save_confusion_matrix(best_metrics["confusion_matrix"], output_dir / "confusion_matrix.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="CT pseudo-label semi-supervised training.")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    args = parser.parse_args()
    run_training(args.config)


if __name__ == "__main__":
    main()
