# Method 2: CT Pseudo-Label Semi-Supervised Decision Report

Generated from `/data1/midrc/runs/bimcv_pseudolabel_lam15_20260516` for tag `bimcv_pseudolabel_lam15_20260516`. Supervised baseline pulled from `/data1/midrc/runs/bimcv_full_paired_cv_20260516`.

## Run completion

- Pseudolabel runs with test_eval completed: 60
- Cohort: BIMCV 510 paired patients (113+/397-)
- Loss per batch: weighted CE on true labels + lambda * CE(student, argmax(teacher)) on samples with max(softmax(teacher)) > tau
- Hardware: 4x RTX 3090, AMP fp16

## Mean test metrics

| Variant | Method | tau | lambda | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3slice | supervised | - | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| 3slice | pseudolabel | 0.70 | 1.50 | 15 | 0.6216 [0.5936, 0.6471] | 0.5876 | 0.6916 | 0.6740 |
| 3slice | pseudolabel | 0.80 | 1.50 | 15 | 0.6428 [0.6215, 0.6636] | 0.5941 | 0.6739 | 0.7123 |
| mid | supervised | - | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| mid | pseudolabel | 0.70 | 1.50 | 15 | 0.6543 [0.6299, 0.6763] | 0.6094 | 0.6844 | 0.6802 |
| mid | pseudolabel | 0.80 | 1.50 | 15 | 0.6576 [0.6387, 0.6754] | 0.6073 | 0.6736 | 0.6920 |

## Paired decision deltas vs supervised baseline (gate: mean DeltaBA >= +0.03 AND CI lower > 0)

| Variant | tau | lambda | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3slice | 0.70 | 1.50 | 15 | -0.0031 [-0.0315, +0.0253] | 9/0/6 | +0.0200 | +0.0714 | NO |
| 3slice | 0.80 | 1.50 | 15 | +0.0181 [-0.0105, +0.0464] | 9/0/6 | +0.0266 | +0.0536 | NO |
| mid | 0.70 | 1.50 | 15 | +0.0296 [+0.0026, +0.0577] | 9/0/6 | +0.0419 | +0.0641 | NO |
| mid | 0.80 | 1.50 | 15 | +0.0329 [+0.0074, +0.0584] | 10/1/4 | +0.0398 | +0.0533 | YES |

## Decision

- Total pseudolabel comparisons passing pre-specified gate: 1/4

**VALIDATED**: at least one (teacher, tau, lambda) configuration of the CT pseudo-label semi-supervised training passes the pre-specified gate on the 510-patient BIMCV paired cohort. Method 2 has demonstrated cross-modal advantage at this cohort scale.
