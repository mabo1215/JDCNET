"""Cross-modal contrastive alignment (Method 1).

Two-stage training:
  Stage 1: InfoNCE / NT-Xent pretrain over paired (X-ray, CT) batches.
           Trains a ResNet-18 X-ray encoder and a ResNet-18 CT encoder
           with separate MLP projection heads. Patient pairing is the
           sole supervision signal.
  Stage 2: Drop CT branch; replace the X-ray backbone's fc head with
           a fresh linear classifier and fine-tune with weighted CE
           on the labelled paired manifest.

The checkpoint emitted at the end of Stage 2 is a plain
ResNet18Classifier state dict so the existing ``jdcnet_exp.evaluate``
entry point can be reused for held-out test scoring.
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
import torchvision.models as tvm
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
from .data import (
    MedicalImageManifestDataset,
    _loader_runtime_kwargs,
    create_dataloaders,
    load_filtered_manifests,
)
from .metrics import compute_metrics
from .models import ResNet18Classifier


@dataclass
class ContrastiveConfig:
    enabled: bool = True
    embedding_dim: int = 128
    projection_hidden_dim: int = 128
    pretrain_epochs: int = 100
    pretrain_lr: float = 1e-4
    pretrain_weight_decay: float = 1e-4
    pretrain_batch_size: int = 128
    temperature: float = 0.07
    teacher_image_column: str = "teacher_image_path"
    finetune_epochs: int = 50
    finetune_lr: float = 3e-4
    freeze_ct_encoder: bool = False
    init_from_imagenet: bool = True


class ProjectionHead(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _build_resnet18_backbone(init_from_imagenet: bool) -> tuple[nn.Module, int]:
    weights = tvm.ResNet18_Weights.IMAGENET1K_V1 if init_from_imagenet else None
    backbone = tvm.resnet18(weights=weights)
    in_features = backbone.fc.in_features
    backbone.fc = nn.Identity()
    return backbone, in_features


def info_nce_loss(z_xray: torch.Tensor, z_ct: torch.Tensor, temperature: float) -> torch.Tensor:
    """Symmetric InfoNCE on L2-normalised projections (CLIP-style)."""
    z_xray = F.normalize(z_xray, dim=1)
    z_ct = F.normalize(z_ct, dim=1)
    logits = (z_xray @ z_ct.T) / temperature
    targets = torch.arange(z_xray.size(0), device=z_xray.device)
    loss_xc = F.cross_entropy(logits, targets)
    loss_cx = F.cross_entropy(logits.T, targets)
    return 0.5 * (loss_xc + loss_cx)


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


def _make_pretrain_loader(
    config: ExperimentConfig, contrastive_cfg: ContrastiveConfig
) -> DataLoader:
    train_manifest, _ = load_filtered_manifests(config)
    if contrastive_cfg.teacher_image_column not in train_manifest.columns:
        raise ValueError(
            f"Pretrain requires column '{contrastive_cfg.teacher_image_column}' in manifest."
        )
    dataset = MedicalImageManifestDataset(
        train_manifest,
        image_size=config.model.input_size,
        is_train=True,
        paired_image_column=contrastive_cfg.teacher_image_column,
        include_paired_image=True,
    )
    kwargs = _loader_runtime_kwargs(config)
    kwargs["batch_size"] = contrastive_cfg.pretrain_batch_size
    kwargs["shuffle"] = True
    kwargs["drop_last"] = True
    return DataLoader(dataset, **kwargs)


def stage1_pretrain(
    config: ExperimentConfig,
    contrastive_cfg: ContrastiveConfig,
    output_dir: Path,
    device: torch.device,
    use_amp: bool,
) -> Path:
    loader = _make_pretrain_loader(config, contrastive_cfg)

    xray_backbone, feat_dim = _build_resnet18_backbone(contrastive_cfg.init_from_imagenet)
    ct_backbone, _ = _build_resnet18_backbone(contrastive_cfg.init_from_imagenet)
    xray_proj = ProjectionHead(feat_dim, contrastive_cfg.projection_hidden_dim, contrastive_cfg.embedding_dim)
    ct_proj = ProjectionHead(feat_dim, contrastive_cfg.projection_hidden_dim, contrastive_cfg.embedding_dim)

    xray_backbone.to(device)
    ct_backbone.to(device)
    xray_proj.to(device)
    ct_proj.to(device)

    params = list(xray_backbone.parameters()) + list(xray_proj.parameters()) + list(ct_proj.parameters())
    if contrastive_cfg.freeze_ct_encoder:
        for p in ct_backbone.parameters():
            p.requires_grad_(False)
    else:
        params += list(ct_backbone.parameters())

    optimizer = optim.AdamW(
        params,
        lr=contrastive_cfg.pretrain_lr,
        weight_decay=contrastive_cfg.pretrain_weight_decay,
    )
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    history: list[dict[str, object]] = []
    for epoch in range(1, contrastive_cfg.pretrain_epochs + 1):
        xray_backbone.train()
        xray_proj.train()
        ct_proj.train()
        ct_backbone.train(mode=not contrastive_cfg.freeze_ct_encoder)

        total_loss = 0.0
        n_batches = 0
        for batch in loader:
            if len(batch) != 3:
                raise RuntimeError("Pretrain loader must yield (xray, ct, label) triples.")
            xray_img, ct_img, _labels = batch
            xray_img = xray_img.to(device, non_blocking=True)
            ct_img = ct_img.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                if contrastive_cfg.freeze_ct_encoder:
                    with torch.no_grad():
                        ct_feat = ct_backbone(ct_img)
                else:
                    ct_feat = ct_backbone(ct_img)
                xray_feat = xray_backbone(xray_img)
                z_xray = xray_proj(xray_feat)
                z_ct = ct_proj(ct_feat)
                loss = info_nce_loss(z_xray, z_ct, contrastive_cfg.temperature)

            if use_amp:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()

            total_loss += float(loss.item())
            n_batches += 1

        mean_loss = total_loss / max(n_batches, 1)
        history.append({"epoch": epoch, "pretrain_loss": mean_loss})
        if epoch == 1 or epoch % 10 == 0 or epoch == contrastive_cfg.pretrain_epochs:
            print(
                f"[{config.experiment_name}] stage1 epoch={epoch} "
                f"pretrain_loss={mean_loss:.4f} batches={n_batches}"
            )

    encoder_path = output_dir / "stage1_xray_encoder.pt"
    torch.save(xray_backbone.state_dict(), encoder_path)
    write_json(history, output_dir / "stage1_history.json")
    print(f"[{config.experiment_name}] stage1 done; encoder saved to {encoder_path}")
    return encoder_path


def _load_stage1_into_classifier(model: ResNet18Classifier, stage1_path: Path) -> int:
    state = torch.load(stage1_path, map_location="cpu")
    own = model.net.state_dict()
    loaded = 0
    for k, v in state.items():
        if k in own and own[k].shape == v.shape:
            own[k] = v
            loaded += 1
    model.net.load_state_dict(own)
    return loaded


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


def stage2_finetune(
    config: ExperimentConfig,
    contrastive_cfg: ContrastiveConfig,
    stage1_path: Path,
    output_dir: Path,
    device: torch.device,
    use_amp: bool,
) -> None:
    train_loader, val_loader = create_dataloaders(config)
    train_manifest, _ = load_filtered_manifests(config)
    class_weights = _compute_class_weights(train_manifest, config.model.num_classes, device)

    model = ResNet18Classifier(num_classes=config.model.num_classes).to(device)
    n_loaded = _load_stage1_into_classifier(model, stage1_path)
    print(f"[{config.experiment_name}] stage2 loaded {n_loaded} tensors from stage1 encoder")

    optimizer = optim.AdamW(
        model.parameters(),
        lr=contrastive_cfg.finetune_lr,
        weight_decay=config.optimization.weight_decay,
    )
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    best_score = -1.0
    history: list[dict[str, object]] = []
    for epoch in range(1, contrastive_cfg.finetune_epochs + 1):
        model.train()
        running_loss = 0.0
        optimizer.zero_grad(set_to_none=True)
        for batch in train_loader:
            if len(batch) == 3:
                images, _paired, labels = batch
            else:
                images, labels = batch
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                logits = model(images)
                loss = F.cross_entropy(logits, labels, weight=class_weights)
            if use_amp:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            running_loss += float(loss.item())

        metrics: dict[str, object] = {
            "epoch": epoch,
            "train_loss": running_loss / max(len(train_loader), 1),
        }
        metrics.update(_evaluate(model, val_loader, device))
        score = float(metrics.get("balanced_accuracy", metrics["accuracy"]))
        if score > best_score:
            best_score = score
            torch.save(model.state_dict(), output_dir / "best.pt")
            write_json(metrics, output_dir / "best_metrics.json")
        history.append(metrics)
        print(
            f"[{config.experiment_name}] stage2 epoch={epoch} "
            f"loss={metrics['train_loss']:.4f} ba={metrics.get('balanced_accuracy', 'NaN')}"
        )

    write_json(history, output_dir / "history.json")
    write_history_csv(history, output_dir / "history.csv")
    save_learning_curves(history, output_dir / "learning_curves.png")

    model.load_state_dict(torch.load(output_dir / "best.pt", map_location=device))
    best_metrics = _evaluate(model, val_loader, device)
    write_json(best_metrics, output_dir / "best_metrics.json")
    save_confusion_matrix(best_metrics["confusion_matrix"], output_dir / "confusion_matrix.png")


def _load_config_with_contrastive(config_path: str | Path) -> tuple[ExperimentConfig, ContrastiveConfig]:
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
    contrastive_cfg = ContrastiveConfig(**(payload.get("contrastive") or {}))
    return base, contrastive_cfg


def run_training(config_path: str | Path) -> None:
    config, contrastive_cfg = _load_config_with_contrastive(config_path)
    set_seed(config.seed)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = bool(config.optimization.amp and device.type == "cuda")

    stage1_path = output_dir / "stage1_xray_encoder.pt"
    if stage1_path.exists():
        print(f"[{config.experiment_name}] stage1 cached at {stage1_path}; skipping")
    else:
        stage1_path = stage1_pretrain(config, contrastive_cfg, output_dir, device, use_amp)

    if (output_dir / "best.pt").exists():
        print(f"[{config.experiment_name}] stage2 already complete; skipping")
        return
    stage2_finetune(config, contrastive_cfg, stage1_path, output_dir, device, use_amp)


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-stage CT/X-ray contrastive alignment.")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    args = parser.parse_args()
    run_training(args.config)


if __name__ == "__main__":
    main()
