# BIMCV Path C Results from the R3090 Host

This directory stores the R3090 fixed-split Path C outputs that were previously pulled into `docs/tmp/3090_pathc`.
They are kept under `src/results/` because they are numerical experiment artifacts rather than temporary notes.

## Experiment

- Cohort: BIMCV paired binary cohort.
- Path C split: balanced validation re-split intended to increase positive validation support.
- Training patients: 398 total, with 338 negative and 60 positive patients.
- Validation patients: 114 total, with 60 negative and 54 positive patients.
- Backbone: ImageNet-pretrained ResNet-18 for both CT teacher and X-ray student.
- Seeds: 42, 43, 44, 45.
- Compared rows: CT teacher, X-ray supervised student, and cross-modal CT-to-X-ray logit KD.

## Main fixed-split result

| Method | Balanced accuracy | ROC-AUC | Sensitivity | Specificity |
|---|---:|---:|---:|---:|
| CT teacher | 0.729 ? 0.026 | 0.731 ? 0.018 | 0.627 | 0.831 |
| X-ray supervised | 0.623 ? 0.012 | 0.651 ? 0.021 | 0.623 | 0.624 |
| Cross-modal logit KD | 0.626 ? 0.010 | 0.659 ? 0.020 | 0.568 | 0.684 |

KD minus supervised balanced-accuracy deltas by seed: -0.008, +0.013, +0.024, -0.019.
Mean delta is +0.002, with mixed seed direction. The exact four-pair Wilcoxon value is descriptive only: two-sided p=0.875, one-sided KD-greater p=0.4375.

## Interpretation

The re-split confirms CT-teacher feasibility but does not convert cross-modal KD into a statistically validated architecture.
The X-ray supervised baseline drops under the deliberately harder train/validation redistribution, and CT-to-X-ray logit KD remains effectively tied with it.
This supports the manuscript framing: CT supervision is feasible, while cross-modal KD remains evidence-bounded and unstable rather than a validated positive-transfer mechanism.

## Files

- `summary.csv`: per-run metrics pulled from the remote host.
- `aggregate_summary.csv`: paper-facing mean and standard-deviation aggregates by method.
- `paired_seed_delta.csv`: seed-paired KD-minus-supervised balanced-accuracy deltas.
- `analysis.txt`: original text summary generated after the pull.
- `runs/*/best_metrics.json`: per-run best-checkpoint metrics.
- `remote_status.txt`: remote completion/provenance snapshot.
