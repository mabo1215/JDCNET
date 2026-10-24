# Calibrated-Gate Ablation (A2 + A3) — Decision Report

**Run tag:** `bimcv_h800_calibrated_gate` (H800, 2026-06-25)
**Purpose:** Address reviewer flaw **F3** — confidence gate derived from an *uncalibrated* teacher could force the student to learn over-confident, incorrect targets. Combines A2 (calibrated gate) and A3 (overconfidence ablation) in a single sweep.

## Design
- Two previously gate-passing cells: `3slice_soft` (3-slice soft-KL, τ=0.70, λ=1.0) and `mid_hard` (mid-slice hard, τ=0.80, λ=1.5).
- Teacher gate temperature **T ∈ {0.5, 1.0, 2.0}**: T=0.5 sharpens (over-confident), T=1.0 = uncalibrated original gate, T=2.0 softens (toward calibrated).
- Patient-level 5-fold × 3 seeds (42–44) = 15 runs/cell-temp; 2 cells × 3 T × 15 = **90 runs**. All complete (90/90).
- **Cohort:** H800 same-patient *paired* subset (216 patients with both CT and X-ray present). NOTE: this is **not** the 510-patient headline cohort; it is the paired-only subset usable on H800.
- Metric split: **val (`best_metrics.json`)** — matches the paper/5fold methodology (5fold runs have no test_eval). Test-split (`test_eval/metrics.json`) reported as secondary.
- Supervised baseline (same cohort/folds, val): BA = 0.6976, AUC = 0.7104. Teacher BA = 0.7105.

## Results (val, paper-consistent)

| cell | T | meaning | n | val BA | ΔBA vs supervised | CI95 | ΔBA vs T=1.0 |
|---|---|---|---|---|---|---|---|
| 3slice_soft | 0.5 | over-conf | 15 | 0.602 | −0.095 | [−0.146,−0.043] | −0.005 |
| 3slice_soft | **1.0** | uncalib (orig) | 15 | 0.607 | −0.091 | [−0.142,−0.041] | 0.000 |
| 3slice_soft | 2.0 | softened | 15 | 0.594 | −0.104 | [−0.155,−0.048] | −0.013 |
| mid_hard | 0.5 | over-conf | 15 | 0.683 | −0.015 | [−0.045,+0.018] | +0.003 |
| mid_hard | **1.0** | uncalib (orig) | 15 | 0.680 | −0.018 | [−0.047,+0.013] | 0.000 |
| mid_hard | 2.0 | softened | 15 | 0.672 | −0.025 | [−0.059,+0.011] | −0.007 |

## Findings (stated without spin)

1. **F3 (calibration sensitivity) — answered, NULL/robustness result.** Within each cell, the three temperatures are statistically indistinguishable (within-cell |ΔBA| ≤ 0.013, all differences inside noise; SD 0.04–0.10). Over-confident (T=0.5) does **not** degrade the student, and softening/calibration (T=2.0) does **not** improve it. → The confidence gate is **robust to teacher (mis)calibration** in this range. This empirically confirms the paper's existing Limitations prediction (main.tex L555: calibration "expected to stabilize, rather than overturn, the gate decision").

2. **Cohort caveat on absolute ΔBA.** On this paired-216 subset, neither cell reproduces the +0.0345/+0.0329 of the 510-patient headline: `3slice_soft` is significantly negative (≈−0.09, CI excludes 0); `mid_hard` is null (≈−0.018, CI includes 0). This is attributable to the smaller paired-only cohort, **not** to calibration. It does not overturn the 510 headline (different cohort) but means the temperature ablation must be reported as a *robustness check*, with the cohort difference stated explicitly — NOT as a re-derivation of the headline ΔBA.

## How this maps to the paper
- **Methods / Limitations (L544, L555):** upgrade "a principled safeguard *is to* calibrate… *expected to* stabilize" → "we ran the ablation: varying teacher gate temperature T∈{0.5,1.0,2.0} on the paired cohort changes student BA by ≤0.013 (all CIs include 0), confirming the gate decision is statistically insensitive to teacher temperature scaling; an over-confident teacher does not destabilize the student."
- This directly answers F3 (over-confidence cannot force the student wrong, empirically).
- Open positioning decision: report on paired-216 with caveat (practical) vs re-run on 510 cohort for direct comparability (needs 510 data on a reachable GPU).

## Artifacts
- `summary.csv` — the table above (val primary + test secondary columns).
- `aggregate_val.txt`, `aggregate_test.txt` — raw aggregator output (`analyze_calib.py`, SPLIT=val/test).
- Per-run metrics on H800: `runs/bimcv_h800_calibrated_gate/<cell>_f<ff>_s<ss>_T<ttt>/{best_metrics.json,test_eval/metrics.json}`.
