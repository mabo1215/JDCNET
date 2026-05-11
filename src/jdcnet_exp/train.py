from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch
from torch import nn, optim
from torch.utils.data import DataLoader

from .artifacts import save_confusion_matrix, save_learning_curves, write_history_csv, write_json
from .config import ExperimentConfig, load_config
from .data import create_dataloaders, load_filtered_manifests
from .distillation import (
    attention_transfer_loss,
    crd_loss,
    distillation_loss,
    dist_loss,
    dkd_loss,
    feature_hint_loss,
    lung_mask_distill_loss,
    modality_hallucination_loss,
    projected_attention_loss,
    prototype_distill_loss,
    teacher_confidence_gate,
)
from .metrics import compute_metrics
from .models import build_model


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _unpack_batch(batch: tuple[torch.Tensor, ...]) -> tuple[torch.Tensor, torch.Tensor | None, torch.Tensor]:
    if len(batch) == 2:
        images, labels = batch
        return images, None, labels
    if len(batch) == 3:
        images, teacher_images, labels = batch
        return images, teacher_images, labels
    raise ValueError(f"Unexpected batch structure with {len(batch)} elements.")


def _forward_model(
    model: nn.Module,
    images: torch.Tensor,
    paired_images: torch.Tensor | None,
    ) -> torch.Tensor:
    if paired_images is not None:
        try:
            return model(images, paired_images)
        except TypeError:
            return model(images)
    return model(images)


def _forward_model_outputs(
    model: nn.Module,
    images: torch.Tensor,
    paired_images: torch.Tensor | None,
) -> dict[str, object]:
    if hasattr(model, "forward_with_features"):
        try:
            return model.forward_with_features(images, paired_images)
        except TypeError:
            return model.forward_with_features(images)
    return {"logits": _forward_model(model, images, paired_images)}


def _compute_class_weights(train_manifest, num_classes: int, device: torch.device) -> torch.Tensor:
    counts = train_manifest["label"].value_counts().reindex(range(num_classes), fill_value=0).astype(float)
    non_zero_counts = counts.replace(0, np.nan)
    weights = counts.sum() / (len(counts) * non_zero_counts)
    weights = weights.fillna(0.0)
    return torch.tensor(weights.to_numpy(), dtype=torch.float32, device=device)


def evaluate_model(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, object]:
    model.eval()
    all_labels: list[int] = []
    all_probabilities: list[np.ndarray] = []

    with torch.no_grad():
        for batch in loader:
            images, paired_images, labels = _unpack_batch(batch)
            images = images.to(device)
            if paired_images is not None:
                paired_images = paired_images.to(device)
            labels = labels.to(device)
            logits = _forward_model(model, images, paired_images)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()
            all_probabilities.append(probabilities)
            all_labels.extend(labels.cpu().tolist())

    stacked_probabilities = np.concatenate(all_probabilities, axis=0)
    return compute_metrics(all_labels, stacked_probabilities)


def run_training(config: ExperimentConfig) -> None:
    set_seed(config.seed)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_manifest, _ = load_filtered_manifests(config)
    train_loader, val_loader = create_dataloaders(config)
    class_weights = _compute_class_weights(train_manifest, config.model.num_classes, device)

    model = build_model(config.model).to(device)
    teacher_model = None
    student_hint_adapter = None
    teacher_hint_adapter = None
    if config.distillation.enabled:
        teacher_model = build_model(
            config.model.__class__(
                name="teacher",
                num_classes=config.model.num_classes,
                input_size=config.model.input_size,
                use_dpe=config.model.use_dpe,
                use_mhra=config.model.use_mhra,
                use_dfpn=True,
                paired_input=False,
                backbone=getattr(config.model, "backbone", "custom"),
            )
        ).to(device)
        teacher_checkpoint = Path(config.distillation.teacher_checkpoint)
        if not teacher_checkpoint.exists():
            raise FileNotFoundError(
                f"Teacher checkpoint not found: {teacher_checkpoint}"
        )
        teacher_model.load_state_dict(torch.load(teacher_checkpoint, map_location=device))
        teacher_model.eval()
        if config.distillation.feature_hint_weight > 0.0:
            student_hint_adapter = nn.Linear(128, config.distillation.feature_hint_dim, bias=False).to(device)
            teacher_hint_adapter = nn.Linear(256, config.distillation.feature_hint_dim, bias=False).to(device)
        if config.distillation.modality_hallucination_weight > 0.0:
            hallucination_head = nn.Sequential(
                nn.Linear(128, 256, bias=True),
                nn.ReLU(inplace=True),
                nn.Linear(256, 256, bias=True),
            ).to(device)
        else:
            hallucination_head = None
        if config.distillation.crd_weight > 0.0:
            student_crd_adapter = nn.Linear(128, config.distillation.feature_hint_dim, bias=False).to(device)
            teacher_crd_adapter = nn.Linear(256, config.distillation.feature_hint_dim, bias=False).to(device)
        else:
            student_crd_adapter = None
            teacher_crd_adapter = None
    else:
        hallucination_head = None
        student_crd_adapter = None
        teacher_crd_adapter = None

    # Tier-B-lite: anatomical-mask predictor (frozen) and EMA class prototypes.
    lung_mask_predictor = None
    if config.distillation.enabled and config.distillation.lung_mask_weight > 0.0:
        try:
            import torchxrayvision as xrv  # type: ignore

            lung_mask_predictor = xrv.baseline_models.chestx_det.PSPNet().to(device)
            lung_mask_predictor.eval()
            for param in lung_mask_predictor.parameters():
                param.requires_grad_(False)
        except Exception as exc:
            raise RuntimeError(
                "torchxrayvision is required when lung_mask_weight > 0. "
                "Install with `pip install torchxrayvision` or set the weight "
                "to 0 to disable the anatomical-mask term."
            ) from exc

    prototypes: torch.Tensor | None = None
    if config.distillation.enabled and config.distillation.prototype_weight > 0.0:
        prototypes = torch.zeros(
            config.model.num_classes, 1, device=device
        )  # placeholder; correct shape allocated on first batch.

    optimization_parameters: list[nn.Parameter] = list(model.parameters())
    if student_hint_adapter is not None and teacher_hint_adapter is not None:
        optimization_parameters.extend(student_hint_adapter.parameters())
        optimization_parameters.extend(teacher_hint_adapter.parameters())
    if hallucination_head is not None:
        optimization_parameters.extend(hallucination_head.parameters())
    if student_crd_adapter is not None and teacher_crd_adapter is not None:
        optimization_parameters.extend(student_crd_adapter.parameters())
        optimization_parameters.extend(teacher_crd_adapter.parameters())

    optimizer = optim.AdamW(
        optimization_parameters,
        lr=config.optimization.learning_rate,
        weight_decay=config.optimization.weight_decay,
    )

    best_score = -1.0
    history: list[dict[str, object]] = []

    for epoch in range(1, config.optimization.epochs + 1):
        model.train()
        running_loss = 0.0

        for batch in train_loader:
            images, teacher_images, labels = _unpack_batch(batch)
            images = images.to(device)
            if teacher_images is not None:
                teacher_images = teacher_images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            student_outputs = _forward_model_outputs(model, images, teacher_images)
            student_logits = student_outputs["logits"]

            if config.distillation.enabled and teacher_model is not None:
                with torch.no_grad():
                    teacher_inputs = teacher_images if teacher_images is not None else images
                    teacher_outputs = _forward_model_outputs(teacher_model, teacher_inputs, None)
                teacher_logits = teacher_outputs["logits"]
                kd_sample_weights = None
                if config.distillation.confidence_gate_enabled:
                    kd_sample_weights = teacher_confidence_gate(
                        teacher_logits=teacher_logits,
                        labels=labels,
                        threshold=config.distillation.confidence_gate_threshold,
                        floor=config.distillation.confidence_gate_floor,
                        power=config.distillation.confidence_gate_power,
                        requires_correct=config.distillation.confidence_gate_requires_correct,
                    )
                loss = distillation_loss(
                    student_logits=student_logits,
                    teacher_logits=teacher_logits,
                    labels=labels,
                    temperature=config.distillation.temperature,
                    alpha=config.distillation.alpha,
                    class_weights=class_weights,
                    sample_weights=kd_sample_weights,
                )
                if config.distillation.attention_transfer_weight > 0.0:
                    loss = loss + config.distillation.attention_transfer_weight * attention_transfer_loss(
                        student_feature=student_outputs["deepest_feature"],
                        teacher_feature=teacher_outputs.get("refined_feature", teacher_outputs["deepest_feature"]),
                    )
                if config.distillation.projected_attention_weight > 0.0:
                    loss = loss + config.distillation.projected_attention_weight * projected_attention_loss(
                        student_feature=student_outputs["deepest_feature"],
                        teacher_feature=teacher_outputs.get("refined_feature", teacher_outputs["deepest_feature"]),
                        confidence_weights=kd_sample_weights,
                    )
                if (
                    config.distillation.feature_hint_weight > 0.0
                    and student_hint_adapter is not None
                    and teacher_hint_adapter is not None
                ):
                    loss = loss + config.distillation.feature_hint_weight * feature_hint_loss(
                        student_feature=student_outputs["deepest_feature"],
                        teacher_feature=teacher_outputs.get("refined_feature", teacher_outputs["deepest_feature"]),
                        student_adapter=student_hint_adapter,
                        teacher_adapter=teacher_hint_adapter,
                    )
                if (
                    config.distillation.modality_hallucination_weight > 0.0
                    and hallucination_head is not None
                ):
                    loss = loss + config.distillation.modality_hallucination_weight * modality_hallucination_loss(
                        student_feature=student_outputs["deepest_feature"],
                        teacher_feature=teacher_outputs.get("refined_feature", teacher_outputs["deepest_feature"]),
                        hallucination_head=hallucination_head,
                    )
                if (
                    config.distillation.crd_weight > 0.0
                    and student_crd_adapter is not None
                    and teacher_crd_adapter is not None
                ):
                    loss = loss + config.distillation.crd_weight * crd_loss(
                        student_feature=student_outputs["deepest_feature"],
                        teacher_feature=teacher_outputs.get("refined_feature", teacher_outputs["deepest_feature"]),
                        labels=labels,
                        student_adapter=student_crd_adapter,
                        teacher_adapter=teacher_crd_adapter,
                        temperature=config.distillation.crd_temperature,
                    )
                if config.distillation.dkd_weight > 0.0:
                    loss = loss + config.distillation.dkd_weight * dkd_loss(
                        student_logits=student_logits,
                        teacher_logits=teacher_logits,
                        labels=labels,
                        temperature=config.distillation.temperature,
                        alpha=config.distillation.dkd_alpha,
                        beta=config.distillation.dkd_beta,
                    )
                if config.distillation.dist_weight > 0.0:
                    loss = loss + config.distillation.dist_weight * dist_loss(
                        student_logits=student_logits,
                        teacher_logits=teacher_logits,
                        temperature=config.distillation.temperature,
                        beta=config.distillation.dist_beta,
                        gamma=config.distillation.dist_gamma,
                    )
                if config.distillation.prototype_weight > 0.0 and prototypes is not None:
                    student_emb = student_outputs["embedding"]
                    teacher_emb = teacher_outputs["embedding"]
                    if prototypes.shape[-1] != student_emb.shape[-1]:
                        prototypes = torch.zeros(
                            config.model.num_classes,
                            student_emb.shape[-1],
                            device=device,
                        )
                    proto_loss, prototypes = prototype_distill_loss(
                        student_embedding=student_emb,
                        teacher_embedding=teacher_emb,
                        labels=labels,
                        prototypes=prototypes,
                        num_classes=config.model.num_classes,
                        ema=config.distillation.prototype_ema,
                        temperature=config.distillation.prototype_temperature,
                    )
                    loss = loss + config.distillation.prototype_weight * proto_loss
                if (
                    config.distillation.lung_mask_weight > 0.0
                    and lung_mask_predictor is not None
                ):
                    with torch.no_grad():
                        gray = images.mean(dim=1, keepdim=True)
                        xrv_in = gray * 2048.0 - 1024.0
                        if xrv_in.shape[-1] != config.distillation.lung_mask_input_size:
                            xrv_in = nn.functional.interpolate(
                                xrv_in,
                                size=config.distillation.lung_mask_input_size,
                                mode="bilinear",
                                align_corners=False,
                            )
                        seg_logits = lung_mask_predictor(xrv_in)
                        # PSPNet target order: ['Left Clavicle', 'Right Clavicle',
                        # 'Left Scapula', 'Right Scapula', 'Left Lung', 'Right Lung',
                        # ...]; channels 4 and 5 are the two lungs.
                        lung = torch.sigmoid(seg_logits[:, 4:6]).sum(dim=1, keepdim=True).clamp(0.0, 1.0)
                    loss = loss + config.distillation.lung_mask_weight * lung_mask_distill_loss(
                        student_spatial_feature=student_outputs["deepest_feature"],
                        lung_mask=lung,
                    )
            else:
                loss = nn.functional.cross_entropy(student_logits, labels, weight=class_weights)

            loss.backward()
            optimizer.step()
            running_loss += float(loss.item())

        metrics = evaluate_model(model, val_loader, device)
        metrics["epoch"] = epoch
        metrics["train_loss"] = running_loss / max(len(train_loader), 1)
        history.append(metrics)
        print(
            f"[{config.experiment_name}] epoch={epoch} "
            f"loss={metrics['train_loss']:.4f} acc={metrics['accuracy']:.4f} "
            f"f1={metrics['macro_f1']:.4f} auc={metrics['roc_auc']}"
        )

        score = float(metrics.get("balanced_accuracy", metrics["accuracy"]))
        if score > best_score:
            best_score = score
            torch.save(model.state_dict(), output_dir / "best.pt")
            write_json(metrics, output_dir / "best_metrics.json")

    write_json(history, output_dir / "history.json")
    write_history_csv(history, output_dir / "history.csv")
    save_learning_curves(history, output_dir / "learning_curves.png")

    model.load_state_dict(torch.load(output_dir / "best.pt", map_location=device))
    best_metrics = evaluate_model(model, val_loader, device)
    write_json(best_metrics, output_dir / "best_metrics.json")
    save_confusion_matrix(best_metrics["confusion_matrix"], output_dir / "confusion_matrix.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train JDCNET experiment scaffold.")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    args = parser.parse_args()

    config = load_config(args.config)
    run_training(config)


if __name__ == "__main__":
    main()
