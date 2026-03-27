from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_metrics(labels: list[int], probabilities: np.ndarray) -> dict[str, object]:
    predictions = probabilities.argmax(axis=1)
    num_classes = probabilities.shape[1]
    matrix = confusion_matrix(labels, predictions, labels=list(range(num_classes)))
    metrics: dict[str, object] = {
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "precision": float(precision_score(labels, predictions, average="binary", zero_division=0)),
        "recall": float(recall_score(labels, predictions, average="binary", zero_division=0)),
        "confusion_matrix": matrix.tolist(),
    }

    if num_classes == 2 and matrix.shape == (2, 2):
        true_negative, false_positive = matrix[0, 0], matrix[0, 1]
        denominator = true_negative + false_positive
        metrics["specificity"] = float(true_negative / denominator) if denominator else 0.0

    try:
        if num_classes == 2:
            metrics["roc_auc"] = float(roc_auc_score(labels, probabilities[:, 1]))
        else:
            metrics["roc_auc"] = float(
                roc_auc_score(labels, probabilities, multi_class="ovr", average="macro")
            )
    except ValueError:
        metrics["roc_auc"] = None

    return metrics
