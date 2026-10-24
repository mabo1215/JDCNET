# Stage A 510-Patient Extended Paired CV Decision Report

Generated from `/data1/midrc/runs/bimcv_full_paired_cv_20260516` for tag `bimcv_full_paired_cv_20260516`.

## Run completion

- Completed test metrics: 240/240.
- Cohort: BIMCV 113+/397- = 510 patients (4.5x previous 226 balanced).
- Execution: 4x RTX 3090, batch_size=512, num_workers=8, concurrency=4 per GPU, weighted-CE + weighted sampler for 3.5:1 imbalance.

## Mean test metrics

| Variant | Method | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| mid | teacher | 15 | 0.6697 [0.6449, 0.6946] | 0.6531 | 0.8085 | 0.7472 |
| mid | supervised | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| mid | plain_kd | 15 | 0.6144 [0.5785, 0.6479] | 0.5645 | 0.6788 | 0.6760 |
| mid | gated_kd | 15 | 0.6027 [0.5629, 0.6406] | 0.5281 | 0.6471 | 0.6604 |
| 3slice | teacher | 15 | 0.6758 [0.6533, 0.6964] | 0.6623 | 0.8180 | 0.7538 |
| 3slice | supervised | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| 3slice | plain_kd | 15 | 0.5883 [0.5640, 0.6159] | 0.5197 | 0.6149 | 0.6546 |
| 3slice | gated_kd | 15 | 0.5989 [0.5603, 0.6357] | 0.5162 | 0.6539 | 0.6472 |
| proj | teacher | 15 | 0.6557 [0.6350, 0.6755] | 0.6338 | 0.7764 | 0.7281 |
| proj | supervised | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| proj | plain_kd | 15 | 0.6091 [0.5738, 0.6433] | 0.5337 | 0.6213 | 0.6542 |
| proj | gated_kd | 15 | 0.6110 [0.5792, 0.6409] | 0.5381 | 0.6156 | 0.6550 |
| drr | teacher | 15 | 0.6343 [0.6029, 0.6638] | 0.6099 | 0.7501 | 0.7050 |
| drr | supervised | 15 | 0.6247 [0.5985, 0.6478] | 0.5675 | 0.6203 | 0.6742 |
| drr | plain_kd | 15 | 0.6238 [0.5887, 0.6562] | 0.5769 | 0.6802 | 0.6750 |
| drr | gated_kd | 15 | 0.5610 [0.5339, 0.5913] | 0.4288 | 0.4326 | 0.6128 |

## Paired decision deltas (pre-specified gate: mean DeltaBA >= +0.03 AND CI lower > 0)

| Variant | Comparison | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |
|---|---|---:|---:|---:|---:|---:|---:|
| mid | gated_vs_supervised | 15 | -0.0220 [-0.0549, +0.0106] | 5/0/10 | -0.0394 | +0.0268 | NO |
| mid | gated_vs_plain | 15 | -0.0117 [-0.0461, +0.0236] | 6/2/7 | -0.0364 | -0.0318 | NO |
| mid | teacher_vs_supervised | 15 | +0.0450 [+0.0188, +0.0693] | 11/0/4 | +0.0856 | +0.1883 | YES |
| mid | plain_vs_supervised | 15 | -0.0103 [-0.0505, +0.0279] | 9/0/6 | -0.0030 | +0.0586 | NO |
| 3slice | gated_vs_supervised | 15 | -0.0258 [-0.0790, +0.0272] | 7/0/8 | -0.0513 | +0.0336 | NO |
| 3slice | gated_vs_plain | 15 | +0.0105 [-0.0409, +0.0623] | 9/0/6 | -0.0035 | +0.0390 | NO |
| 3slice | teacher_vs_supervised | 15 | +0.0511 [+0.0254, +0.0795] | 12/0/3 | +0.0948 | +0.1977 | YES |
| 3slice | plain_vs_supervised | 15 | -0.0363 [-0.0625, -0.0130] | 4/0/11 | -0.0478 | -0.0054 | NO |
| proj | gated_vs_supervised | 15 | -0.0137 [-0.0573, +0.0297] | 5/0/10 | -0.0294 | -0.0047 | NO |
| proj | gated_vs_plain | 15 | +0.0020 [-0.0441, +0.0484] | 7/1/7 | +0.0044 | -0.0057 | NO |
| proj | teacher_vs_supervised | 15 | +0.0310 [-0.0023, +0.0650] | 9/0/6 | +0.0663 | +0.1562 | NO |
| proj | plain_vs_supervised | 15 | -0.0156 [-0.0611, +0.0271] | 9/0/6 | -0.0339 | +0.0010 | NO |
| drr | gated_vs_supervised | 15 | -0.0637 [-0.0953, -0.0335] | 3/0/12 | -0.1387 | -0.1877 | NO |
| drr | gated_vs_plain | 15 | -0.0628 [-0.1100, -0.0165] | 6/0/9 | -0.1480 | -0.2476 | NO |
| drr | teacher_vs_supervised | 15 | +0.0096 [-0.0345, +0.0564] | 8/1/6 | +0.0424 | +0.1298 | NO |
| drr | plain_vs_supervised | 15 | -0.0009 [-0.0460, +0.0430] | 8/0/7 | +0.0094 | +0.0600 | NO |

## Decision

- Total comparisons passing pre-specified gate: 2/16
- Gated_vs_supervised comparisons passing: 0/4

**NOT YET VALIDATED**: no gated_vs_supervised comparison passes the gate on the 510-patient cohort. Trigger Stage B (MIDRC 559 full processing) or Stage C (X-ray pretrain) per decision tree.
