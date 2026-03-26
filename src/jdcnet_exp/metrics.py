from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score


def compute_metrics(labels: list[int], probabilities: np.ndarray) -> dict[str, object]:
    predictions = probabilities.argmax(axis=1)
    metrics: dict[str, object] = {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
    }

    num_classes = probabilities.shape[1]
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
