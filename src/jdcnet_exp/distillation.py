from __future__ import annotations

import torch
from torch import nn
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


def attention_transfer_loss(
    student_feature: torch.Tensor,
    teacher_feature: torch.Tensor,
) -> torch.Tensor:
    student_attention = student_feature.pow(2).mean(dim=1, keepdim=True)
    teacher_attention = teacher_feature.pow(2).mean(dim=1, keepdim=True)
    if teacher_attention.shape[-2:] != student_attention.shape[-2:]:
        teacher_attention = F.interpolate(
            teacher_attention,
            size=student_attention.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )
    student_attention = F.normalize(student_attention.flatten(1), dim=1)
    teacher_attention = F.normalize(teacher_attention.flatten(1), dim=1)
    return F.mse_loss(student_attention, teacher_attention)


def feature_hint_loss(
    student_feature: torch.Tensor,
    teacher_feature: torch.Tensor,
    student_adapter: nn.Module,
    teacher_adapter: nn.Module,
) -> torch.Tensor:
    student_vector = F.adaptive_avg_pool2d(student_feature, (1, 1)).flatten(1)
    teacher_vector = F.adaptive_avg_pool2d(teacher_feature, (1, 1)).flatten(1)
    student_projection = F.normalize(student_adapter(student_vector), dim=1)
    teacher_projection = F.normalize(teacher_adapter(teacher_vector), dim=1)
    return F.mse_loss(student_projection, teacher_projection)
