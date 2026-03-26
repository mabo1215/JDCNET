from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch import nn, optim
from torch.utils.data import DataLoader

from .config import ExperimentConfig, load_config
from .data import create_dataloaders
from .distillation import distillation_loss
from .metrics import compute_metrics
from .models import build_model


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate_model(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, object]:
    model.eval()
    all_labels: list[int] = []
    all_probabilities: list[np.ndarray] = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            logits = model(images)
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
    train_loader, val_loader = create_dataloaders(config)

    model = build_model(config.model.name, config.model.num_classes).to(device)
    teacher_model = None
    if config.distillation.enabled:
        teacher_model = build_model("teacher", config.model.num_classes).to(device)
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

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            student_logits = model(images)

            if config.distillation.enabled and teacher_model is not None:
                with torch.no_grad():
                    teacher_logits = teacher_model(images)
                loss = distillation_loss(
                    student_logits=student_logits,
                    teacher_logits=teacher_logits,
                    labels=labels,
                    temperature=config.distillation.temperature,
                    alpha=config.distillation.alpha,
                )
            else:
                loss = nn.functional.cross_entropy(student_logits, labels)

            loss.backward()
            optimizer.step()
            running_loss += float(loss.item())

        metrics = evaluate_model(model, val_loader, device)
        metrics["epoch"] = epoch
        metrics["train_loss"] = running_loss / max(len(train_loader), 1)
        history.append(metrics)

        if metrics["accuracy"] > best_accuracy:
            best_accuracy = float(metrics["accuracy"])
            torch.save(model.state_dict(), output_dir / "best.pt")

    with open(output_dir / "history.json", "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train JDCNET experiment scaffold.")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    args = parser.parse_args()

    config = load_config(args.config)
    run_training(config)


if __name__ == "__main__":
    main()
