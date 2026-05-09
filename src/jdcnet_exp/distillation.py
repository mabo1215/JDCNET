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
    student_vector = (F.adaptive_avg_pool2d(student_feature, (1, 1)).flatten(1)
                      if student_feature.dim() == 4 else student_feature)
    teacher_vector = (F.adaptive_avg_pool2d(teacher_feature, (1, 1)).flatten(1)
                      if teacher_feature.dim() == 4 else teacher_feature)
    student_projection = F.normalize(student_adapter(student_vector), dim=1)
    teacher_projection = F.normalize(teacher_adapter(teacher_vector), dim=1)
    return F.mse_loss(student_projection, teacher_projection)


def modality_hallucination_loss(
    student_feature: torch.Tensor,
    teacher_feature: torch.Tensor,
    hallucination_head: nn.Module,
) -> torch.Tensor:
    """Modality hallucination (Hoffman et al. 2016).

    A trainable hallucination head maps the X-ray student feature into a
    teacher-modality (CT) feature space; the loss is the L2 distance between
    the hallucinated CT feature and the true CT feature from the paired
    teacher input. The teacher feature is detached so gradients flow only
    through the student branch and the hallucination head.
    """
    student_vec = (F.adaptive_avg_pool2d(student_feature, (1, 1)).flatten(1)
                   if student_feature.dim() == 4 else student_feature)
    teacher_vec = (F.adaptive_avg_pool2d(teacher_feature.detach(), (1, 1)).flatten(1)
                   if teacher_feature.dim() == 4 else teacher_feature.detach())
    hallucinated = hallucination_head(student_vec)
    return F.mse_loss(hallucinated, teacher_vec)


def crd_loss(
    student_feature: torch.Tensor,
    teacher_feature: torch.Tensor,
    labels: torch.Tensor,
    student_adapter: nn.Module,
    teacher_adapter: nn.Module,
    temperature: float = 0.07,
) -> torch.Tensor:
    """Contrastive representation distillation (Tian et al. 2020), simplified.

    Uses an in-batch supervised contrastive objective rather than a memory
    bank, which is appropriate for our small batch size (16). Student and
    teacher features are projected and L2-normalized; the positive pair for
    each anchor is the matching teacher embedding for the same patient,
    and negatives are all other teacher embeddings in the batch with a
    different label. Temperature is fixed at 0.07 (standard CRD/SimCLR).
    """
    s_vec = (F.adaptive_avg_pool2d(student_feature, (1, 1)).flatten(1)
             if student_feature.dim() == 4 else student_feature)
    t_vec = (F.adaptive_avg_pool2d(teacher_feature.detach(), (1, 1)).flatten(1)
             if teacher_feature.dim() == 4 else teacher_feature.detach())
    s_proj = F.normalize(student_adapter(s_vec), dim=1)
    t_proj = F.normalize(teacher_adapter(t_vec), dim=1)
    logits = s_proj @ t_proj.t() / temperature  # (B, B)
    targets = torch.arange(logits.size(0), device=logits.device)
    return F.cross_entropy(logits, targets)


def dkd_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    labels: torch.Tensor,
    temperature: float = 4.0,
    alpha: float = 1.0,
    beta: float = 8.0,
) -> torch.Tensor:
    """Decoupled Knowledge Distillation (Zhao et al. CVPR 2022).

    Decomposes the standard KD objective into a Target Class KD (TCKD) term
    that aligns the binary {target, non-target} probabilities, and a
    Non-target Class KD (NCKD) term that aligns the within-non-target
    distribution. For binary classification the NCKD term reduces to the
    log-prob of the single non-target class, which still provides a useful
    decoupled gradient signal distinct from plain KD. Default alpha/beta
    follow the CVPR 2022 paper's chest-X-ray-friendly setting.
    """
    n_classes = student_logits.size(1)
    one_hot = F.one_hot(labels, num_classes=n_classes).float()

    p_t = F.softmax(teacher_logits / temperature, dim=1)
    p_s = F.softmax(student_logits / temperature, dim=1)

    # Target Class KD
    pt_target = (p_t * one_hot).sum(dim=1, keepdim=True)
    pt_non = 1.0 - pt_target
    ps_target = (p_s * one_hot).sum(dim=1, keepdim=True)
    ps_non = 1.0 - ps_target
    eps = 1e-8
    tckd = (
        pt_target * (torch.log(pt_target + eps) - torch.log(ps_target + eps))
        + pt_non * (torch.log(pt_non + eps) - torch.log(ps_non + eps))
    ).sum(dim=1).mean() * (temperature ** 2)

    # Non-target Class KD: distribute over the remaining classes
    if n_classes > 2:
        mask = 1.0 - one_hot
        p_t_non = F.softmax(teacher_logits / temperature - 1e9 * one_hot, dim=1)
        p_s_non = F.log_softmax(student_logits / temperature - 1e9 * one_hot, dim=1)
        nckd = (mask * p_t_non * (torch.log(p_t_non + eps) - p_s_non)).sum(dim=1).mean() * (temperature ** 2)
    else:
        # Binary case: NCKD collapses to a single non-target log-prob; we use
        # a symmetric KL on that single off-target probability.
        nckd = torch.tensor(0.0, device=student_logits.device)
    return alpha * tckd + beta * nckd


def prototype_distill_loss(
    student_embedding: torch.Tensor,
    teacher_embedding: torch.Tensor,
    labels: torch.Tensor,
    prototypes: torch.Tensor,
    num_classes: int,
    ema: float = 0.95,
    temperature: float = 0.1,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Tier-B class-prototype distillation.

    Maintain an EMA estimate of the teacher's class centroids in the shared
    embedding space and minimise the cross-entropy of the student's
    cosine-similarity-to-prototype distribution against the true labels.
    Returns the per-step loss and the updated prototypes (so the caller can
    persist them across batches).

    student_embedding / teacher_embedding: [B, D] (e.g., 512 for ResNet-18).
    prototypes: [num_classes, D] (initialised to zero on first call).
    """
    teacher_emb = teacher_embedding.detach()
    new_prototypes = prototypes.clone()
    for c in range(num_classes):
        mask = labels == c
        if mask.any():
            class_mean = teacher_emb[mask].mean(dim=0)
            class_mean = F.normalize(class_mean, dim=0)
            if (prototypes[c].abs().sum() > 0).item():
                updated = ema * prototypes[c] + (1.0 - ema) * class_mean
            else:
                updated = class_mean
            new_prototypes[c] = F.normalize(updated, dim=0)

    if (new_prototypes.abs().sum() == 0).item():
        # First batch where no class has been observed yet.
        return student_embedding.sum() * 0.0, new_prototypes

    student_norm = F.normalize(student_embedding, dim=1)
    logits_proto = student_norm @ new_prototypes.t() / temperature
    return F.cross_entropy(logits_proto, labels), new_prototypes


def lung_mask_distill_loss(
    student_spatial_feature: torch.Tensor,
    lung_mask: torch.Tensor,
) -> torch.Tensor:
    """Tier-B anatomical-mask distillation.

    Encourage the student's deepest spatial activation map (mean of squared
    channels) to peak inside the lung region predicted by a frozen external
    chest segmentation model. Both signals are spatially pooled to the
    student feature resolution and L2-normalised before MSE.

    student_spatial_feature: [B, C, h, w].
    lung_mask: [B, 1, H, W] in [0, 1] from a frozen lung-segmentation network.
    """
    target = F.adaptive_avg_pool2d(lung_mask, student_spatial_feature.shape[-2:])
    student_attn = student_spatial_feature.pow(2).mean(dim=1, keepdim=True)
    student_attn = F.normalize(student_attn.flatten(1), dim=1)
    target = F.normalize(target.flatten(1), dim=1)
    return F.mse_loss(student_attn, target)


def dist_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    temperature: float = 4.0,
    beta: float = 1.0,
    gamma: float = 1.0,
) -> torch.Tensor:
    """DIST: Knowledge Distillation from a Stronger Teacher (Yang et al. NeurIPS 2022).

    Replaces KL alignment with two correlation-based terms:
      - inter-class: Pearson correlation between the teacher and student
        per-sample logit profiles, encouraging the student to preserve the
        teacher's class ranking rather than its absolute scale.
      - intra-class: Pearson correlation across the batch for each class,
        encouraging consistency of teacher/student ordering for samples
        within the same class.
    This is well suited when the teacher is much stronger than the student,
    as is the case when CT contains richer information than X-ray.
    """
    p_t = F.softmax(teacher_logits / temperature, dim=1)
    p_s = F.softmax(student_logits / temperature, dim=1)

    def pearson(a: torch.Tensor, b: torch.Tensor, dim: int) -> torch.Tensor:
        a_c = a - a.mean(dim=dim, keepdim=True)
        b_c = b - b.mean(dim=dim, keepdim=True)
        num = (a_c * b_c).sum(dim=dim)
        den = a_c.norm(dim=dim) * b_c.norm(dim=dim) + 1e-8
        return num / den

    inter = (1.0 - pearson(p_t, p_s, dim=1)).mean()
    intra = (1.0 - pearson(p_t, p_s, dim=0)).mean()
    return beta * inter + gamma * intra
