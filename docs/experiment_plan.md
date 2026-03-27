# Experiment Plan

## Goal

Build a reproducible experimental pipeline for cross-modality chest X-ray and CT classification with knowledge distillation.

## Planned Tasks

### Data Layer

- use a CSV manifest with columns:
  - `image_path`
  - `label`
  - `modality`
  - `split`
  - `patient_id`

- enforce patient-level splits when possible
- support at least two modalities: `xray` and `ct`

## Baselines

- teacher-only baseline
- student-only baseline
- same-modality distillation baseline
- cross-modality distillation baseline

## Metrics

- accuracy
- macro-F1
- ROC-AUC
- confusion matrix

## Recommended Tables

- overall comparison table
- ablation on temperature and distillation weight
- cross-modality transfer table
- repeated-run statistics table

## Recommended Figures

- ROC curves
- confusion matrices
- training/validation loss curves
- feature-space visualization if justified

## Deliverables In `src/`

- reusable config objects
- dataset loader
- simple teacher/student CNN backbones
- distillation loss
- train entrypoint
- evaluation entrypoint
- patient-level split generator
- ablation config generator
- run summarization utilities
- paper asset generation utilities
