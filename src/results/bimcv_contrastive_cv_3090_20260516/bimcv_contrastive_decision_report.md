# Method 1: Cross-Modal Contrastive Alignment Decision Report

Generated from `/data1/midrc/runs/bimcv_contrastive_cv_20260516` for tag `bimcv_contrastive_cv_20260516`. Supervised baseline pulled from `/data1/midrc/runs/bimcv_full_paired_cv_20260516`.

## Run completion

- Contrastive runs with test_eval completed: 60
- Cohort: BIMCV 510 paired patients (113+/397-)
- Stage 1 InfoNCE pretrain on (X-ray, CT) pairs; Stage 2 supervised fine-tune of X-ray encoder + classifier
- Hardware: 4x RTX 3090, AMP fp16

## Mean test metrics

| Variant | Method | tau | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| 3slice | supervised | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| 3slice | contrastive | 0.07 | 15 | 0.6274 [0.5942, 0.6573] | 0.5570 | 0.5716 | 0.6736 |
| 3slice | contrastive | 0.20 | 15 | 0.6327 [0.6095, 0.6556] | 0.5769 | 0.6230 | 0.6607 |
| mid | supervised | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| mid | contrastive | 0.07 | 15 | 0.6163 [0.5896, 0.6420] | 0.5662 | 0.6323 | 0.6526 |
| mid | contrastive | 0.20 | 15 | 0.6196 [0.5943, 0.6434] | 0.5593 | 0.6020 | 0.6792 |

## Paired decision deltas vs supervised baseline (gate: mean DeltaBA >= +0.03 AND CI lower > 0)

| Variant | tau | Comparison | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 3slice | 0.07 | contrastive_vs_supervised | 15 | +0.0027 [-0.0226, +0.0296] | 7/0/8 | -0.0105 | -0.0486 | NO |
| 3slice | 0.20 | contrastive_vs_supervised | 15 | +0.0080 [-0.0201, +0.0371] | 7/1/7 | +0.0094 | +0.0027 | NO |
| mid | 0.07 | contrastive_vs_supervised | 15 | -0.0084 [-0.0384, +0.0268] | 5/0/10 | -0.0013 | +0.0120 | NO |
| mid | 0.20 | contrastive_vs_supervised | 15 | -0.0051 [-0.0305, +0.0200] | 5/0/10 | -0.0082 | -0.0183 | NO |

## Decision

- Total contrastive comparisons passing pre-specified gate: 0/4

**NOT VALIDATED**: no contrastive configuration passes the gate on the 510-patient cohort. Continue to Method 2 (CT pseudo-label semi-supervised) per the recommended execution order.
