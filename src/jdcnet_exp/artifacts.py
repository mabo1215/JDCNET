from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def write_json(payload: object, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def write_history_csv(history: list[dict[str, object]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(history).to_csv(output_path, index=False)


def save_learning_curves(history: list[dict[str, object]], path: str | Path) -> None:
    if not history:
        return

    frame = pd.DataFrame(history)
    figure, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)

    axes[0].plot(frame["epoch"], frame["train_loss"], marker="o", color="#2a6f97")
    axes[0].set_title("Training Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(alpha=0.3, linestyle="--")

    axes[1].plot(frame["epoch"], frame["accuracy"], marker="o", label="Accuracy", color="#355070")
    if "macro_f1" in frame:
        axes[1].plot(frame["epoch"], frame["macro_f1"], marker="o", label="Macro-F1", color="#b56576")
    if "roc_auc" in frame and frame["roc_auc"].notna().any():
        axes[1].plot(frame["epoch"], frame["roc_auc"], marker="o", label="ROC-AUC", color="#6d597a")
    axes[1].set_title("Validation Metrics")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Score")
    axes[1].grid(alpha=0.3, linestyle="--")
    axes[1].legend(loc="lower right")

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def save_confusion_matrix(
    matrix: list[list[int]],
    path: str | Path,
    class_labels: list[str] | None = None,
) -> None:
    labels = class_labels or [str(index) for index in range(len(matrix))]
    figure, axis = plt.subplots(figsize=(5, 4), constrained_layout=True)
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xticks(range(len(labels)))
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.set_yticks(range(len(labels)))
    axis.set_yticklabels(labels)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("True")
    axis.set_title("Confusion Matrix")

    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            axis.text(col_index, row_index, str(value), ha="center", va="center", color="black")

    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
