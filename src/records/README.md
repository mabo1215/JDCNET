# Archived experiment records

Aggregate records used to regenerate the statistics reported in the third
revision of the manuscript. These files contain only derived metrics; no
image data or patient identifiers.

| File | Content | Provenance |
|---|---|---|
| `jdcnet510_initial_grid_per_fold.tsv` | Per fold/seed test-fold BA, specificity and ROC-AUC for the supervised baseline and the initial 8-configuration hard-target JDCNet grid on the 510-patient cohort | Copied from the 3090 host summary `bimcv_pseudolabel_cv_3090_20260516/bimcv_pseudolabel_status.tsv` |
| `jdcnet510_initial_grid_deltas.csv` | Paired ΔBA summaries of the initial grid | Same run, `bimcv_pseudolabel_deltas.csv` |
| `jdcnet510_grid_summary.csv` | All 16 JDCNet configurations: paired ΔBA mean, 95% percentile-bootstrap CI over the 15 fold/seed cells, and positive/zero/negative fold/seed counts, with the sweep stage | Initial grid from the deltas file above; extension stages A (λ=1.5, hard) and B (soft-KL, λ=1.0) transcribed from the run report `docs/tmp/report516.md` (the per-fold files of those stages were not retained locally) |
| `contrastive510_*.csv` | Contrastive-alignment comparator on the 510-patient cohort | `bimcv_contrastive_cv_3090_20260516` |
| `biomedclip226_deltas.csv` | BiomedCLIP comparator; note the baseline is the 226-patient cohort | `bimcv_biomedclip_cv_3090_20260516` |
| `ctvariants226_deltas.csv` | CT teacher-view comparison on the 226-patient cohort | `bimcv_ct_variants_cv_3090_20260516` |

Regenerate the derived statistics with:

```powershell
python -m jdcnet_exp.revision_stats
```

Outputs are written to `src/records/derived/`.
