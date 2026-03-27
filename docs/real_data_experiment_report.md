# Real-Data Experiment Report

## Scope

This report summarizes the first fully executable real-data experiment cycle for the current JDCNET revision.

## Data Source

- local dataset root: `D:\source\covid-chestxray-dataset`
- modalities actually available in the local dataset: `X-ray`, `CT`
- MRI availability in the local dataset: not present

## Executed Manifests

- `src/data/covid_real/covid_xray_all_manifest.csv`
  - 783 images
  - 424 patients
  - 504 positive
  - 279 negative
- `src/data/covid_real/covid_ct_all_manifest.csv`
  - 63 images
  - 25 patients
  - 59 positive
  - 4 negative
- `src/data/covid_real/covid_paired_xray_target_manifest.csv`
  - 26 X-ray target images
  - 19 paired patients
  - 22 positive
  - 4 negative

## Executed Matrix

- teacher-only X-ray on the full X-ray manifest
- teacher-only CT on the full CT manifest
- student-only X-ray on the paired cohort
- same-modality distillation on the paired cohort
- cross-modality distillation from CT teacher to X-ray student
- repeated runs with seeds `42, 43, 44, 45`
- temperature/alpha ablation on the cross-modality setting

## Main Quantitative Takeaway

- `cross-modality distillation` is the strongest paired-cohort result in this revision.
- Mean results across four seeds:
  - accuracy: `0.875 ± 0.144`
  - macro-F1: `0.714 ± 0.330`
  - balanced accuracy: `0.750 ± 0.289`
- Compared with the paired X-ray student-only baseline:
  - accuracy improves from `0.750` to `0.875`
  - macro-F1 improves from `0.429` to `0.714`

## Important Limitations

- The paired validation set contains only `4` X-ray images.
- The CT branch is extremely imbalanced at the patient level.
- The current teacher/student models are lightweight placeholders, not yet a final submission-grade JDCNET implementation.
- The ablation grid is executable, but the present cohort is too small to support stable hyperparameter conclusions.

## Generated Paper Assets

- `paper/results/covid_matrix_main_results.csv`
- `paper/results/covid_matrix_ablation_results.csv`
- `paper/images/generated/covid_matrix_main.png`
- `paper/images/generated/covid_matrix_ablation.png`

## Recommendation

The current revision is now suitable as a reproducible proof-of-concept manuscript draft, but not yet as a serious MICCAI submission. The highest-value next step is to expand the paired cohort or add a stronger held-out dataset before further polishing the theory.
