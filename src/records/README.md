# Archived experiment records

Aggregate records used to regenerate the statistics reported in the third
revision of the manuscript. These files contain only derived metrics; no
image data, per-image predictions, or patient identifiers.

## Per-run records (primary source)

| File | Content | Provenance |
|---|---|---|
| `runs510_per_run.csv` | One row per original run (915 runs: CT-only references, logit KD, JDCNet and contrastive alignment on the 510-patient cohort, the 226-patient view comparison, and the balanced-subset gated-KD scan): validation BA and test-partition BA, AUC, macro-F1, sensitivity, specificity, Brier score and confusion counts | Collected from the run directories of the original 4x3090 host and its H800 mirror with `collect_run_records.py` |
| `sup128_per_run.csv` | The 240 batch-128 supervised restarts of the pre-registered supplementary experiment (16 per fold/seed cell) | Same collector, run directory of the round-3 experiment |
| `gatedscan_balanced_summary.csv` | Balanced-subset gated logit-KD scan: eight (T, threshold) cells, mean BA and ΔBA against the scan's own supervised baseline (T=4 with threshold 0.55 was not run) | Cell summary of the scan run `bimcv_only_calibration_scan_20260514` |

## Earlier summary records (kept for traceability)

| File | Content | Provenance |
|---|---|---|
| `jdcnet510_initial_grid_per_fold.tsv` | Per fold/seed test-fold BA, specificity and ROC-AUC for the supervised baseline and the initial 8-configuration hard-target JDCNet grid on the 510-patient cohort | 3090 host summary `bimcv_pseudolabel_cv_3090_20260516/bimcv_pseudolabel_status.tsv` |
| `jdcnet510_initial_grid_deltas.csv` | Paired ΔBA summaries of the initial grid | Same run, `bimcv_pseudolabel_deltas.csv` |
| `jdcnet510_grid_summary.csv` | All 16 JDCNet configurations: paired ΔBA mean, 95% percentile-bootstrap CI over the 15 fold/seed cells, and positive/zero/negative counts, with the sweep stage | Initial grid from the deltas file above; extension stages A and B transcribed from the run report. The per-fold records of all stages are now in `runs510_per_run.csv`, which supersedes this file |
| `contrastive510_*.csv` | Contrastive-alignment comparator on the 510-patient cohort | `bimcv_contrastive_cv_3090_20260516` |
| `biomedclip226_deltas.csv` | BiomedCLIP comparator; the baseline is the 226-patient cohort | `bimcv_biomedclip_cv_3090_20260516` |
| `ctvariants226_deltas.csv` | CT teacher-view comparison on the 226-patient cohort | `bimcv_ct_variants_cv_3090_20260516` |

## Derived statistics (`derived/`)

| File | Script | Needs per-image predictions |
|---|---|---|
| `revision_round3_stats.json` | `revision_stats.py` | No |
| `round3_full_analysis.json` | `round3_full_analysis.py` | No |
| `round3_restart_analysis.json` | `round3_restart_analysis.py` (cell-level analyses of the supplementary experiment, including the primary nested comparison) | No |
| `round3_prediction_analysis.json` | `round3_prediction_analysis.py` (reproduction check, patient-level bootstrap, external MIDRC analysis with DeLong and McNemar tests, teacher calibration) | Yes |
| `inference_benchmark.json` | `benchmark_inference.py` | No |
| `round3_tables.tex`, `round3_tableA1.tex` | `make_round3_tables.py` | No |

The pre-registered analysis plan is `docs/round3_experiment_plan.md`.

Cell-level statistics are regenerated from the records in this folder, for
example:

```powershell
python src/jdcnet_exp/round3_full_analysis.py
python src/jdcnet_exp/round3_restart_analysis.py
```

`round3_prediction_analysis.py` additionally needs the per-image prediction
files (`--preds`). These are indexed by BIMCV and MIDRC identifiers and are
not distributed with the repository because of the source data-use terms;
they are available from the corresponding author on request. Of the 615 X-ray
student checkpoints re-run for predictions (240 JDCNet, 15 supervised batch-512,
120 logit-KD, 240 batch-128 restarts), the BA recomputed from the stored predictions
matches the recorded value for 613; the other two differ by 0.006 and 0.022
BA (listed under `reproduction_mismatches`). Cell-level statistics use the
recorded values.
