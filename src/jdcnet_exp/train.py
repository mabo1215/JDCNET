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
from .distillation import distillation_loss
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
            )
        ).to(device)
        teacher_checkpoint = Path(config.distillation.teacher_checkpoint)
        if not teacher_checkpoint.exists():
            raise FileNotFoundError(
                f"Teacher checkpoint not found: {teacher_checkpoint}"
            )
        teacher_model.load_state_dict(torch.load(teacher_checkpoint, map_location=device))
        teacher_model.eval()

    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.optimization.learning_rate,
        weight_decay=config.optimization.weight_decay,
    )

    best_accuracy = -1.0
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
            student_logits = _forward_model(model, images, teacher_images)

            if config.distillation.enabled and teacher_model is not None:
                with torch.no_grad():
                    teacher_inputs = teacher_images if teacher_images is not None else images
                    teacher_logits = teacher_model(teacher_inputs)
                loss = distillation_loss(
                    student_logits=student_logits,
                    teacher_logits=teacher_logits,
                    labels=labels,
                    temperature=config.distillation.temperature,
                    alpha=config.distillation.alpha,
                    class_weights=class_weights,
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

        if metrics["accuracy"] > best_accuracy:
            best_accuracy = float(metrics["accuracy"])
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
