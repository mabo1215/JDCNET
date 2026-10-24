# DRR Teacher CV Decision Report (bimcv_drr_cv_20260515)
runs parsed: 165

## EXP1: DRR Teacher 5-fold (seeds 42-44)
Completed fold-seed cells: 30

### Method means
| Method | n | Mean BA | Mean ± std |
|---|---|---|---|
| teacher | 30 | 0.6295 | 0.0808 |
| supervised | 30 | 0.6090 | 0.0766 |
| plain_kd | 15 | 0.5879 | 0.0993 |
| gated_kd | 30 | 0.6019 | 0.0685 |

### Paired deltas vs supervised
| Comparison | n | Mean ΔBA | 95% CI | Pos / Neg |
|---|---|---|---|---|
| teacher − supervised | 30 | +0.0205 | [-0.0204, +0.0620] | 17/11 | ✗ FAIL |
| gated KD − supervised | 30 | -0.0071 | [-0.0416, +0.0257] | 15/15 | ✗ FAIL |
| gated KD − plain KD | 15 | +0.0378 | [-0.0011, +0.0829] | 9/4 | ≈ NEAR |

## EXP2: Extended Seeds 45-47 (CT mid-slice)
Completed fold-seed cells: 15

### Method means
| Method | n | Mean BA | Mean ± std |
|---|---|---|---|
| teacher | 15 | 0.6489 | 0.0678 |
| supervised | 15 | 0.6167 | 0.0674 |
| gated_kd | 15 | 0.6039 | 0.0580 |

### Paired deltas vs supervised
| Comparison | n | Mean ΔBA | 95% CI | Pos / Neg |
|---|---|---|---|---|
| teacher − supervised | 15 | +0.0322 | [-0.0266, +0.0851] | 11/4 | ≈ NEAR |
| gated KD − supervised | 15 | -0.0128 | [-0.0478, +0.0225] | 5/8 | ✗ FAIL |

### Exp2 gated KD vs supervised: mean=-0.0128, pos=5/15

## EXP3: Batch=64 Sensitivity (seeds 42-44)
Completed fold-seed cells: 15

### Method means
| Method | n | Mean BA | Mean ± std |
|---|---|---|---|
| gated_kd | 15 | 0.6129 | 0.0535 |

### Paired deltas vs supervised
| Comparison | n | Mean ΔBA | 95% CI | Pos / Neg |
|---|---|---|---|---|

## COMBINED: exp2 seeds 45-47 + calibration scan T=4,thr=0.50 (seeds 42-44)
(Check calibration_scan cell_summary for seeds 42-44 T=4,thr=0.50 data)
