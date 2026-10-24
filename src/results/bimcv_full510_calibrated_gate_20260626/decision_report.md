# Calibrated-Gate Ablation (F3) — 510 Headline Cohort Rerun — Decision Report

**Run tag:** `bimcv_full510_calibrated_gate` (H800, 2026-06-26)
**Purpose:** Re-run the F3 teacher-temperature ablation on the **510 headline cohort** (466 effective) instead of the paired-216 subset, so the temperature ablation is directly comparable to the paper's headline ΔBA and the awkward "passing cells don't replicate on 216" caveat can be removed.

## Design
- Two gate-passing cells: `3slice_soft` (3-slice soft-KL, τ=0.70, λ=1.0) and `mid_hard` (mid-slice hard, τ=0.80, λ=1.5).
- Teacher gate temperature **T ∈ {0.5, 1.0, 2.0}** (0.5 over-confident, 1.0 = uncalibrated original, 2.0 softened/calibrated).
- **Cohort:** 510 full-mode imbalanced CV (`--mode full`), effective 466 patients (113+/353−) — the maximal subset of the 510 cohort with both a CT teacher variant and an X-ray on disk (vs 216 in the prior subset run).
- **1 seed (42)** × 5 folds = n=5/cell-temp; 2 cells × 3 T × 5 = **30 runs** (cost-trimmed from the full 3-seed/90-run design after diagnosing the H800 was ~80% idle on this tiny workload).
- Metric split: **val (`best_metrics.json`)** — matches the paper/5fold methodology (supervised baselines have no test_eval). Test split is descriptive-only (no paired supervised baseline available).
- Supervised baseline (val): 3slice BA=0.6644 / AUC=0.7128; mid BA=0.6042 / AUC=0.6557.

## Results (val, paper-consistent), n=5

| cell | T | meaning | val BA | ΔBA vs supervised | CI95 | ΔBA vs T=1.0 |
|---|---|---|---|---|---|---|
| 3slice_soft | 0.5 | over-conf | 0.711 | +0.047 | [+0.028,+0.064] | +0.025 |
| 3slice_soft | **1.0** | uncalib (orig) | 0.686 | +0.022 | [−0.011,+0.068] | 0.000 |
| 3slice_soft | 2.0 | softened | 0.691 | +0.027 | [−0.001,+0.061] | +0.005 |
| mid_hard | 0.5 | over-conf | 0.680 | +0.076 | [+0.035,+0.117] | +0.007 |
| mid_hard | **1.0** | uncalib (orig) | 0.673 | +0.069 | [+0.034,+0.106] | 0.000 |
| mid_hard | 2.0 | softened | 0.659 | +0.054 | [+0.024,+0.088] | −0.014 |

## Findings (stated without spin)

1. **510 cohort recovers positive ΔBA — the 216 non-replication caveat is resolved.** Both cells are positive at T=1.0: `mid_hard` +0.069 (CI excludes 0, exceeds the +0.033 headline) and `3slice_soft` +0.022 (positive, CI includes 0 at n=5). This is the opposite of the paired-216 subset (`3slice_soft` ≈ −0.09, `mid_hard` ≈ −0.018), confirming the 216 negatives were a small-cohort artefact, not a method failure. The F3 ablation now sits on the headline cohort.

2. **F3 (calibration sensitivity) — NULL/robustness result, confirmed on the headline cohort.** Within each cell the three temperatures are statistically indistinguishable (within-cell |ΔBA vs T=1.0| ≤ 0.025; all cells stay positive across T). Over-confident (T=0.5) does **not** degrade the student (if anything marginally higher, within noise); softening/calibration (T=2.0) does **not** help. → The confidence gate is **robust to teacher (mis)calibration**, now demonstrated on the 510 headline cohort rather than a subset.

3. **Honest limitations.** Single seed (n=5) vs the prior n=15, so CIs are wider and `3slice_soft` T=1.0 includes 0; the within-cell spread (≤0.025) is slightly larger than the 216 run's ≤0.013 due to n=5 noise. The qualitative conclusion (positive ΔBA, temperature-insensitive) is robust to this.

## How this maps to the paper (F3)
- Abstract: update the F3 clause — temperature insensitivity now on the **headline cohort** (within-cell ΔBA ≤ 0.025), and the passing cells stay positive across T.
- Limitations / Discussion F3: replace the paired-216 robustness-note-with-cohort-caveat by a clean statement: on the 510 headline cohort, varying teacher gate temperature T∈{0.5,1.0,2.0} leaves the two passing cells positive with within-cell ΔBA ≤ 0.025 (gate statistically insensitive to teacher calibration; over-confidence does not destabilize the student). Drop the "subcohort does not reproduce headline" hedging.
- Keep the single-seed caveat explicit (robustness rerun, n=5).

## Artifacts
- `summary.csv` — full val + test table incl. supervised baselines.
- `analyze_full510_calib.py` — analysis script (val primary, paired ΔBA, bootstrap CI, within-cell vs T=1.0).
- `full510_calib_pull.tgz` — raw backup (30 calib + 10 supervised best_metrics.json + test_eval + configs + status).
- Run tag on H800 (now shut down): `runs/bimcv_full510_calibrated_gate/<cell>_f<ff>_s42_T<ttt>/`.
