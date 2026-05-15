# GAP-KD/JDCNet-v2 Architecture Change Overview

## Before (Plain Logit KD)

```
┌─────────────────────────────────────────────────────────────────┐
│ CT Volume (Teacher)                 X-ray Image (Student)      │
│                                                                   │
│  ┌──────────────┐                   ┌──────────────┐            │
│  │ CT Encoder   │                   │ Xray Encoder │            │
│  └──────┬───────┘                   └──────┬───────┘            │
│         │                                   │                    │
│         │                                   │                    │
│  ┌──────v───────────────────────────v──────────┐                │
│  │  Logit KD Loss (Unconditional)             │                │
│  │  L_kd = KL(T || S)  [always same α]        │                │
│  └────────────────────────────────────────────┘                │
│         │                                                         │
│  ┌──────v───────────────────────────v──────────┐                │
│  │  Feature Hint / Attention Transfer         │                │
│  │  (Whole image, no anatomical constraint)   │                │
│  └────────────────────────────────────────────┘                │
│                                                                   │
│         ❌ Problem: T predicts wrong                             │
│            → Still force S to mimic (harmful)                    │
│                                                                   │
│         ❌ Problem: No geometry bridge                           │
│            → CT-to-Xray alignment is indirect/noisy             │
│                                                                   │
│         ❌ Problem: Attention over whole image                  │
│            → S learns device artifacts, not disease             │
└─────────────────────────────────────────────────────────────────┘

Result on BIMCV 512:  Cross-modal KD ≈ X-ray supervised (not validated)
```

## After (GAP-KD / JDCNet-v2)

```
┌─────────────────────────────────────────────────────────────────┐
│ MODULE A: Multi-window CT Teacher (Future)                       │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Lung Window  │  │ Mediastinal  │  │ Bone Window  │           │
│  │ CT Encoder   │  │ CT Encoder   │  │ CT Encoder   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│                   ┌────────v────────┐                            │
│                   │ Teacher Logits  │                            │
│                   │ Teacher Confidence                           │
│                   │ Teacher CAM     │                            │
│                   └─────┬──────────┘                             │
│                         │                                        │
│ ┌───────────────────────┴──────────────────────────────┐        │
│ │ MODULE B: Geometry-Aware Projection Bridge          │        │
│ │                                                      │        │
│ │  DRR / MIP / Learned Projection                     │        │
│ │  π(A_T) : CT attention → Xray-like plane            │        │
│ │                                                      │        │
│ └──────────────────────┬───────────────────────────────┘        │
│                        │                                         │
│  ┌─────────────────────┴──────────────────────────────┐         │
│  │                                                     │         │
│  │  ┌──────────────┐                ┌───────────────┐ │         │
│  │  │ Xray Encoder │                │ Confidence    │ │         │
│  │  └──────┬───────┘                │ Gate (Module C)│ │         │
│  │         │                        │               │ │         │
│  │  ┌──────v────────┐       ┌───────v────────────┐  │         │
│  │  │ Student Logits│       │ q_i = 1[ŷ=y]·Conf │  │         │
│  │  │ Student Attn  │       │     ·floor·Power^p │  │         │
│  │  └──────┬────────┘       └───────┬────────────┘  │         │
│  │         │                        │               │         │
│  │  ┌──────v────────────────────────v────────────┐  │         │
│  │  │ MODULE C: Confidence-Gated KD              │  │         │
│  │  │                                            │  │         │
│  │  │ L_kd = α·KL(T||S) · q_i + (1-α)·CE(S,y)  │  │         │
│  │  │                                            │  │         │
│  │  │ ✓ When q_i → 0: suppress harmful transfer │  │         │
│  │  │ ✓ When q_i → 1: full distillation         │  │         │
│  │  │ ✓ Hard CE always active                    │  │         │
│  │  └──────┬────────────────────────────────────┘  │         │
│  │         │                                        │         │
│  │  ┌──────v────────────────────────────────────┐  │         │
│  │  │ MODULE D: Projected Attention Alignment    │  │         │
│  │  │                                            │  │         │
│  │  │ L_attn = |M_lung ⊙ A_S                    │  │         │
│  │  │           - M_lung ⊙ π(A_T)|_1 · q_i     │  │         │
│  │  │                                            │  │         │
│  │  │ ✓ Lung mask: avoid device/frame artifacts │  │         │
│  │  │ ✓ Projected A_T: geometry-aware bridge    │  │         │
│  │  │ ✓ Weighted by q_i: only align confident  │  │         │
│  │  │   & correct cases                          │  │         │
│  │  └──────┬────────────────────────────────────┘  │         │
│  │         │                                        │         │
│  │  ┌──────v────────────────────────────────────┐  │         │
│  │  │ MODULE E: Source-Bias Robust Training      │  │         │
│  │  │ (Future)                                   │  │         │
│  │  │                                            │  │         │
│  │  │ - Source-stratified split                 │  │         │
│  │  │ - Source-adversarial loss                 │  │         │
│  │  │ - Group DRO                                │  │         │
│  │  │ - Out-of-source control                    │  │         │
│  │  └────────────────────────────────────────────┘  │         │
│  │                                                   │         │
│  └─────────────────────────────────────────────────┘         │
│                                                               │
│ Expected Result on MIDRC:                                    │
│   ✓ Δ BA ≥ +0.03~0.05 (vs X-ray supervised)                 │
│   ✓ Paired Wilcoxon p < 0.05, 95% CI lower bound > 0      │
│   ✓ Not a shortcut: source-balanced, anatomy-constrained    │
└───────────────────────────────────────────────────────────────┘
```

## Key Changes in Code

### 1. Confidence Gating (Module C)

**New function: `teacher_confidence_gate()`**

```python
def teacher_confidence_gate(
    teacher_logits,
    labels,
    threshold=0.0,      # minimum confidence to activate
    floor=0.0,          # minimum weight if gate is active
    power=1.0,          # non-linear weighting: q = conf^power
    requires_correct=True,  # multiply by 1[ŷ=y]
) -> torch.Tensor:
    """
    Returns q_i for each sample in batch.
    
    q_i = 0       if (requires_correct & ŷ ≠ y)
    q_i = 0       if (conf < threshold)
    q_i = floor   if (gate active but conf < floor)
    q_i = conf^p  if (gate fully active)
    """
```

### 2. Projected Attention Loss (Module D)

**Modified: `attention_transfer_loss()` → calls `projected_attention_loss()`**

**New function: `projected_attention_loss()`**

```python
def projected_attention_loss(
    student_feature,       # Xray features (B, C, H, W)
    teacher_feature,       # CT features (B, C, H', W')
    anatomical_mask=None,  # Lung mask (B, 1, H, W)
    confidence_weights=None,  # q_i from gate (B,)
) -> torch.Tensor:
    """
    1. Compute attention maps: A = feature^2.mean(dim=1)
    2. If shapes differ: interpolate teacher to student size
    3. If lung mask exists: multiply A *= M_lung
    4. Normalize & compute weighted MSE
    
    If confidence_weights: per-sample weighting
      L = mean(|A_S - A_T|^2 · q_i)
    """
```

### 3. Sample-Weighted Distillation Loss

**Modified: `distillation_loss()`**

```python
def distillation_loss(
    student_logits,
    teacher_logits,
    labels,
    temperature,
    alpha,
    class_weights=None,
    sample_weights=None,  # NEW: q_i from gate
) -> torch.Tensor:
    """
    hard_loss = CE(student, labels)
    
    if sample_weights is None:
        soft_loss = KL(S||T, reduction='batchmean')
    else:
        per_sample_kl = KL(S||T, reduction='none').sum(dim=1)
        soft_loss = mean(per_sample_kl · q_i)
    
    return α·soft_loss + (1-α)·hard_loss
    """
```

### 4. Training Loop Integration

**Modified: `train.py` (line ~220+)**

```python
# After computing teacher_logits
if config.distillation.confidence_gate_enabled:
    kd_sample_weights = teacher_confidence_gate(
        teacher_logits=teacher_logits,
        labels=labels,
        threshold=config.distillation.confidence_gate_threshold,
        floor=config.distillation.confidence_gate_floor,
        power=config.distillation.confidence_gate_power,
        requires_correct=config.distillation.confidence_gate_requires_correct,
    )

# Pass weights to distillation loss
loss_distill = distillation_loss(
    ...,
    sample_weights=kd_sample_weights,  # NEW
)

# Pass weights to attention loss
loss_attn = projected_attention_loss(
    ...,
    confidence_weights=kd_sample_weights,  # NEW
)
```

---

## Experimental Matrix (MIDRC Validation)

Once MIDRC data is ready:

| Row | Configuration | Purpose |
|-----|----------------|---------|
| 1 | X-ray supervised | Baseline (no teacher) |
| 2 | CT teacher | Upper bound / feasibility |
| 3 | Plain CT logit KD | Current best (no gating) |
| 4 | **Gated KD** | Test Module C |
| 5 | **Gated + Projected Attn KD** | Test Modules C+D |
| 6 | Late fusion oracle | Ensemble upper bound |

**Primary Metric**: Balanced Accuracy
- **Success**: Δ BA(row 5) - BA(row 1) ≥ +0.03 to +0.05
- **Statistical**: paired Wilcoxon, 95% CI lower bound > 0
- **Protocol**: same-case resampling, stratified by label

---

## Timeline

- **Phase 1** (now): MIDRC data audit
- **Phase 2** (1-2 days): Prepare MIDRC dataset & splits
- **Phase 3** (12-18 days): GPU training on MIDRC (rows 1-6)
- **Phase 4** (1-2 days): Results evaluation & paper update

**Total**: ~14-20 days to validation decision

---

## Important Notes

✅ **Code ready**: All functions tested on CPU (smoke test)  
✅ **Configurable**: Each component can be toggled  
⏳ **Waiting**: MIDRC data download + audit  
❌ **Not validated**: These modules have only CPU smoke tests, not real training results  

**Paper Status**:
- Current submission: evidence-bounded, cross-modal KD unvalidated
- GAP-KD: explicitly marked as pre-specified future work in limitations
- Only MIDRC GPU experiments can upgrade to "validated architecture"

---

Generated: 2026-05-11 | Status: Framework Ready, Data Audit Pending
