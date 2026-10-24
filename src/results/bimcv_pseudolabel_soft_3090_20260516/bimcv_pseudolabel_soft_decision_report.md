# Method 2: CT Pseudo-Label Semi-Supervised Decision Report

Generated from `/data1/midrc/runs/bimcv_pseudolabel_soft_20260516` for tag `bimcv_pseudolabel_soft_20260516`. Supervised baseline pulled from `/data1/midrc/runs/bimcv_full_paired_cv_20260516`.

## Run completion

- Pseudolabel runs with test_eval completed: 60
- Cohort: BIMCV 510 paired patients (113+/397-)
- Loss per batch: weighted CE on true labels + lambda * CE(student, argmax(teacher)) on samples with max(softmax(teacher)) > tau
- Hardware: 4x RTX 3090, AMP fp16

## Mean test metrics

| Variant | Method | tau | lambda | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3slice | supervised | - | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| 3slice | pseudolabel | 0.70 | 1.00 | 15 | 0.6592 [0.6393, 0.6793] | 0.6181 | 0.7112 | 0.7135 |
| 3slice | pseudolabel | 0.80 | 1.00 | 15 | 0.6505 [0.6232, 0.6724] | 0.6077 | 0.6934 | 0.7000 |
| mid | supervised | - | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| mid | pseudolabel | 0.70 | 1.00 | 15 | 0.6511 [0.6279, 0.6723] | 0.5984 | 0.6567 | 0.6960 |
| mid | pseudolabel | 0.80 | 1.00 | 15 | 0.6478 [0.6303, 0.6659] | 0.6078 | 0.7110 | 0.6925 |

## Paired decision deltas vs supervised baseline (gate: mean DeltaBA >= +0.03 AND CI lower > 0)

| Variant | tau | lambda | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3slice | 0.70 | 1.00 | 15 | +0.0345 [+0.0112, +0.0571] | 10/0/5 | +0.0506 | +0.0910 | YES |
| 3slice | 0.80 | 1.00 | 15 | +0.0258 [-0.0029, +0.0546] | 10/0/5 | +0.0401 | +0.0731 | NO |
| mid | 0.70 | 1.00 | 15 | +0.0264 [+0.0017, +0.0547] | 10/0/5 | +0.0309 | +0.0364 | NO |
| mid | 0.80 | 1.00 | 15 | +0.0231 [-0.0083, +0.0544] | 9/0/6 | +0.0403 | +0.0907 | NO |

## Decision

- Total pseudolabel comparisons passing pre-specified gate: 1/4

**VALIDATED**: at least one (teacher, tau, lambda) configuration of the CT pseudo-label semi-supervised training passes the pre-specified gate on the 510-patient BIMCV paired cohort. Method 2 has demonstrated cross-modal advantage at this cohort scale.
