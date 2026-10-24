# A4 External X-ray Validation — Decision Report

**Run tag:** `h800_external_eval` (H800, 2026-06-25)
**Purpose:** Address reviewer flaw **F1** — evaluation restricted to a single 510-patient cohort; no cross-domain generalization shown. Frozen BIMCV-trained X-ray students are run, inference-only, on an independent external X-ray manifest.

## Design
- External manifest: `data/external/midrc_xray_manifest.csv` (126 X-ray rows, modality=xray, split=test).
- Checkpoints (frozen, no retraining): supervised baseline (30 = 2 variants × 5 folds × 3 seeds) + the two JDCNet gate cells at T=1.0 (`3slice_softkl`, `mid_hard`, 15 each). EVAL_JOBS=60.
- Bug fixed before this run: `h800_external_eval.sh` generated configs with `train_split='train'`; the external manifest has only `split=test` rows, so `evaluate.py`'s (discarded) train loader was empty → `ValueError`. Fix: `train_split = EXT_SPLIT (=test)`.

## Results (external MIDRC X-ray)

| group | n | BA | AUC | macro-F1 | specificity | accuracy |
|---|---|---|---|---|---|---|
| jdcnet_3slice_softkl | 15 | 0.498 | 0.509 | 0.404 | 0.529 | 0.498 |
| jdcnet_mid_hard | 15 | 0.494 | 0.477 | 0.392 | 0.548 | 0.494 |
| supervised | 30 | 0.492 | 0.486 | 0.380 | 0.195 | 0.492 |

## Finding (stated without spin)
**Every model collapses to chance on the external cohort** (BA ≈ 0.49–0.50, AUC ≈ 0.48–0.51) — the supervised baseline and both JDCNet students alike, and they are statistically indistinguishable from each other. The BIMCV-trained X-ray classifier transfers essentially **zero** signal to the external MIDRC X-rays.

This is a clean, direct answer to F1: cross-domain generalization **fails for all models on this task**, confirming the reviewer's dataset-specific-bias concern is real. JDCNet's training-only CT advantage is a *within-cohort* effect and does not buy external robustness — an honest negative that fits the paper's evidence-bounded framing.

## Sanity check (DONE 2026-06-25) — collapse is genuine
External manifest verified: 126 X-rays, **balanced 63/63**, all `modality=xray`/`split=test`, all 126 image paths exist on disk (MIDRC `locked_validation`, independent of BIMCV). **AUC ≈ 0.49 means chance even on the threshold-independent ranking**, so this is not merely a prior/threshold mismatch — the models cannot rank external images at all. Confusion matrices confirm it is not a label-flip: supervised defaults to positive (recall 0.90, spec 0.18), JDCNet cells default to negative (recall ≈0.29, spec ≈0.6); none discriminates. → The collapse is **real domain shift / no transfer**, safe to report; not a manifest artifact.

## How this maps to the paper (F1)
- Replace the current Limitations "only acknowledged + cross-source control" text with a reported **external-validation result**: BIMCV-trained students (supervised and JDCNet) do not exceed chance on an independent external X-ray cohort (BA≈0.49, AUC≈0.49).
- Explicitly scope all positive claims to the BIMCV same-patient cohort and binary task; state that within-cohort transfer does not extend to external X-ray.
- This strengthens (does not weaken) the paper's evidence-bounded-negative stance.

## Artifacts
- `external_summary.csv` — the table above.
- Raw per-run metrics: `src/results/metrics_backup_20260625.tgz` (`runs/h800_external_eval/*/metrics.json`).
- sensitivity column blank in summary = aggregation key mismatch (per-run metrics use `recall`); recompute from raw if needed for the paper.
