# C1 CT Teacher Variant CV Decision Report

Generated on 2026-05-15 UTC from `/data1/midrc/runs/bimcv_ct_variants_cv_20260516`.


## Run completion

- Completed test metrics: 240/240.

- Execution: 4x RTX 3090, batch_size=512, num_workers=8, concurrency=4 per GPU (16 simultaneous ResNet/KD runs).

- Dataset: BIMCV common paired subset after NIfTI/DRR intersection, 226 patients (113+/113-), 5 folds x seeds 42/43/44.


## Mean test metrics

| Variant | Method | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| 3slice | teacher | 15 | 0.6503 [0.6164, 0.6846] | 0.6449 | 0.6395 | 0.7068 |
| 3slice | supervised | 15 | 0.6311 [0.6074, 0.6561] | 0.6217 | 0.6389 | 0.6900 |
| 3slice | plain_kd | 15 | 0.6006 [0.5617, 0.6361] | 0.5937 | 0.5927 | 0.6524 |
| 3slice | gated_kd | 15 | 0.5865 [0.5515, 0.6232] | 0.5805 | 0.5908 | 0.6301 |
| drr | teacher | 15 | 0.6541 [0.6071, 0.6980] | 0.6509 | 0.7086 | 0.6842 |
| drr | supervised | 15 | 0.6311 [0.6072, 0.6555] | 0.6217 | 0.6389 | 0.6900 |
| drr | plain_kd | 15 | 0.5879 [0.5386, 0.6395] | 0.5731 | 0.5808 | 0.6156 |
| drr | gated_kd | 15 | 0.6257 [0.5931, 0.6591] | 0.6180 | 0.6306 | 0.6580 |
| mid | teacher | 15 | 0.6425 [0.6231, 0.6607] | 0.6280 | 0.7553 | 0.6822 |
| mid | supervised | 15 | 0.6311 [0.6072, 0.6554] | 0.6217 | 0.6389 | 0.6900 |
| mid | plain_kd | 15 | 0.6094 [0.5770, 0.6370] | 0.5997 | 0.6091 | 0.6561 |
| mid | gated_kd | 15 | 0.6167 [0.5859, 0.6476] | 0.6003 | 0.6188 | 0.6663 |
| proj | teacher | 15 | 0.6760 [0.6453, 0.7049] | 0.6684 | 0.7342 | 0.7413 |
| proj | supervised | 15 | 0.6311 [0.6070, 0.6550] | 0.6217 | 0.6389 | 0.6900 |
| proj | plain_kd | 15 | 0.6002 [0.5572, 0.6417] | 0.5885 | 0.6375 | 0.6418 |
| proj | gated_kd | 15 | 0.6163 [0.5864, 0.6449] | 0.6052 | 0.6213 | 0.6496 |

## Paired decision deltas

| Variant | Comparison | n | Delta BA mean [95% CI] | +/-/0 | Delta F1 | Delta Spec | Pass |
|---|---|---:|---:|---:|---:|---:|---:|
| 3slice | gated_vs_supervised | 15 | -0.0445 [-0.0917, 0.0002] | 5/10/0 | -0.0413 | -0.0482 | NO |
| 3slice | gated_vs_plain | 15 | -0.0140 [-0.0442, 0.0132] | 8/6/1 | -0.0132 | -0.0019 | NO |
| 3slice | teacher_vs_supervised | 15 | 0.0192 [-0.0128, 0.0575] | 8/5/3 | 0.0232 | 0.0006 | NO |
| drr | gated_vs_supervised | 15 | -0.0053 [-0.0478, 0.0386] | 8/7/0 | -0.0038 | -0.0083 | NO |
| drr | gated_vs_plain | 15 | 0.0378 [-0.0014, 0.0830] | 9/4/2 | 0.0449 | 0.0498 | NO |
| drr | teacher_vs_supervised | 15 | 0.0231 [-0.0234, 0.0663] | 9/6/0 | 0.0292 | 0.0697 | NO |
| mid | gated_vs_supervised | 15 | -0.0144 [-0.0528, 0.0234] | 8/7/0 | -0.0215 | -0.0202 | NO |
| mid | gated_vs_plain | 15 | 0.0073 [-0.0256, 0.0419] | 8/7/1 | 0.0006 | 0.0097 | NO |
| mid | teacher_vs_supervised | 15 | 0.0115 [-0.0244, 0.0463] | 8/7/0 | 0.0062 | 0.1164 | NO |
| proj | gated_vs_supervised | 15 | -0.0148 [-0.0582, 0.0267] | 6/7/2 | -0.0166 | -0.0177 | NO |
| proj | gated_vs_plain | 15 | 0.0161 [-0.0191, 0.0544] | 9/6/0 | 0.0166 | -0.0163 | NO |
| proj | teacher_vs_supervised | 15 | 0.0449 [0.0077, 0.0813] | 9/5/1 | 0.0466 | 0.0952 | YES |

## Decision

- Pre-specified gate (mean Delta BA >= +0.03 and CI lower > 0) passed by 0 gated comparisons.

- C1 does not support a validated KD improvement under the current gate.


Raw CSVs: `ct_variants_summary.csv`, `ct_variants_deltas.csv`.
