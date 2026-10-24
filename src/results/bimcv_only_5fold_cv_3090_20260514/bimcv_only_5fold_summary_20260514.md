# BIMCV-only 5-fold CV summary (2026-05-14)

Balanced patient-level BIMCV-only 5-fold CV; 60/60 runs completed.

## Method means over 15 fold-seed cells

| method | BA mean | BA 95% CI | Macro-F1 mean | Spec mean | AUC mean |
|---|---:|---:|---:|---:|---:|
| teacher_drr | 0.6403 | [0.6076, 0.6722] | 0.6262 | 0.7220 | 0.7059 |
| xray_supervised | 0.5657 | [0.5309, 0.6010] | 0.5358 | 0.5057 | 0.6208 |
| plain_kd | 0.5368 | [0.5031, 0.5693] | 0.5207 | 0.5390 | 0.5753 |
| gated_kd_thr055_proj0000 | 0.5803 | [0.5466, 0.6121] | 0.5608 | 0.5906 | 0.5922 |

## Paired BA deltas

| comparison | mean delta BA | 95% CI | positive / zero / negative |
|---|---:|---:|---:|
| teacher_minus_supervised | +0.0746 | [+0.0314, +0.1144] | 12 / 0 / 3 |
| plain_minus_supervised | -0.0290 | [-0.0842, +0.0240] | 7 / 0 / 8 |
| gated_minus_supervised | +0.0146 | [-0.0264, +0.0531] | 9 / 1 / 5 |
| gated_minus_plain | +0.0435 | [+0.0052, +0.0858] | 7 / 4 / 4 |
| gated_minus_teacher | -0.0600 | [-0.1011, -0.0133] | 3 / 0 / 12 |

## Decision

FAIL validated-architecture gate: gated KD does not reach mean delta BA >= +0.03 with CI lower bound > 0 against both supervised and plain KD.

