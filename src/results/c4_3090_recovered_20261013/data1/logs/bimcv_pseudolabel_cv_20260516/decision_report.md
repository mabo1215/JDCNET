# Method 2: CT Pseudo-Label Semi-Supervised Decision Report

Generated from `/data1/midrc/runs/bimcv_pseudolabel_cv_20260516` for tag `bimcv_pseudolabel_cv_20260516`. Supervised baseline pulled from `/data1/midrc/runs/bimcv_full_paired_cv_20260516`.

## Run completion

- Pseudolabel runs with test_eval completed: 120
- Cohort: BIMCV 510 paired patients (113+/397-)
- Loss per batch: weighted CE on true labels + lambda * CE(student, argmax(teacher)) on samples with max(softmax(teacher)) > tau
- Hardware: 4x RTX 3090, AMP fp16

## Mean test metrics

| Variant | Method | tau | lambda | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3slice | supervised | - | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| 3slice | pseudolabel | 0.70 | 0.50 | 15 | 0.6486 [0.6156, 0.6788] | 0.6027 | 0.6734 | 0.6920 |
| 3slice | pseudolabel | 0.70 | 1.00 | 15 | 0.6312 [0.6045, 0.6565] | 0.5919 | 0.6854 | 0.6866 |
| 3slice | pseudolabel | 0.80 | 0.50 | 15 | 0.6398 [0.6062, 0.6681] | 0.5824 | 0.6346 | 0.6917 |
| 3slice | pseudolabel | 0.80 | 1.00 | 15 | 0.6494 [0.6371, 0.6630] | 0.6109 | 0.7063 | 0.7013 |
| mid | supervised | - | - | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| mid | pseudolabel | 0.70 | 0.50 | 15 | 0.6252 [0.6031, 0.6464] | 0.5867 | 0.6819 | 0.6799 |
| mid | pseudolabel | 0.70 | 1.00 | 15 | 0.6545 [0.6346, 0.6730] | 0.6072 | 0.6808 | 0.7069 |
| mid | pseudolabel | 0.80 | 0.50 | 15 | 0.6391 [0.6111, 0.6617] | 0.5808 | 0.6331 | 0.6886 |
| mid | pseudolabel | 0.80 | 1.00 | 15 | 0.6374 [0.6000, 0.6645] | 0.5892 | 0.6650 | 0.6907 |

## Paired decision deltas vs supervised baseline (gate: mean DeltaBA >= +0.03 AND CI lower > 0)

| Variant | tau | lambda | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3slice | 0.70 | 0.50 | 15 | +0.0239 [-0.0032, +0.0501] | 10/0/5 | +0.0351 | +0.0532 | NO |
| 3slice | 0.70 | 1.00 | 15 | +0.0066 [-0.0182, +0.0330] | 7/0/8 | +0.0244 | +0.0651 | NO |
| 3slice | 0.80 | 0.50 | 15 | +0.0151 [-0.0185, +0.0479] | 9/0/6 | +0.0149 | +0.0143 | NO |
| 3slice | 0.80 | 1.00 | 15 | +0.0247 [+0.0012, +0.0504] | 10/0/5 | +0.0434 | +0.0860 | NO |
| mid | 0.70 | 0.50 | 15 | +0.0005 [-0.0247, +0.0264] | 7/0/8 | +0.0192 | +0.0616 | NO |
| mid | 0.70 | 1.00 | 15 | +0.0298 [-0.0002, +0.0597] | 10/0/5 | +0.0397 | +0.0605 | NO |
| mid | 0.80 | 0.50 | 15 | +0.0144 [-0.0063, +0.0358] | 10/0/5 | +0.0133 | +0.0128 | NO |
| mid | 0.80 | 1.00 | 15 | +0.0127 [-0.0177, +0.0423] | 10/0/5 | +0.0217 | +0.0447 | NO |

## Decision

- Total pseudolabel comparisons passing pre-specified gate: 0/8

**NOT VALIDATED**: no pseudolabel configuration passes the gate on the 510-patient cohort. Continue to Method 3 (Grad-CAM spatial supervision) per the recommended execution order.
