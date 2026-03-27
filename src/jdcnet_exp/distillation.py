from __future__ import annotations

import torch
import torch.nn.functional as F


def distillation_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    labels: torch.Tensor,
    temperature: float,
    alpha: float,
    class_weights: torch.Tensor | None = None,
) -> torch.Tensor:
    hard_loss = F.cross_entropy(student_logits, labels, weight=class_weights)
    soft_loss = F.kl_div(
        F.log_softmax(student_logits / temperature, dim=1),
        F.softmax(teacher_logits / temperature, dim=1),
        reduction="batchmean",
    ) * (temperature ** 2)
    return alpha * soft_loss + (1.0 - alpha) * hard_loss
