# Experiment Code

This directory contains the reproducible experiment scaffold for revising JDCNET toward a submission-ready paper.

## Current Scope

- CSV-manifest based dataset loading
- simple teacher and student CNN backbones
- knowledge distillation training loop
- evaluation entrypoint with common classification metrics
- JSON config based experiment setup
- patient-level manifest splitting
- ablation config generation
- run aggregation and paper-asset export

## Manifest Format

Create a CSV file with the following columns:

- `image_path`
- `label`
- `modality`
- `split`
- `patient_id`

Example:

```csv
image_path,label,modality,split,patient_id
data/xray/p001.png,0,xray,train,p001
data/ct/p001_slice01.png,1,ct,val,p001
```

## Quick Start

Teacher training:

```powershell
python -m jdcnet_exp.train --config .\configs\teacher_xray.json
```

Student distillation:

```powershell
python -m jdcnet_exp.train --config .\configs\student_ct_distill.json
```

Evaluation:

```powershell
python -m jdcnet_exp.evaluate --config .\configs\student_ct_distill.json --checkpoint .\runs\student_ct_distill\best.pt
```

Generate paper figures and result summaries from structured experiment statistics:

```powershell
python -m jdcnet_exp.generate_paper_assets
```

Prepare real manifests from the local COVID chest X-ray dataset:

```powershell
python -m jdcnet_exp.prepare_covid_dataset --dataset-root D:\source\covid-chestxray-dataset --output-dir .\data\covid_real
```

Run the full real-data experiment matrix and export updated assets into `paper/`:

```powershell
python -m jdcnet_exp.run_covid_matrix
```

Create deterministic patient-level splits:

```powershell
python -m jdcnet_exp.split_manifest --input .\data\manifest_raw.csv --output .\data\manifest.csv
```

Generate ablation configs for temperature and alpha:

```powershell
python -m jdcnet_exp.run_ablation --base-config .\configs\student_ct_distill.json --output-dir .\configs\generated_ablation
```

Summarize completed runs:

```powershell
python -m jdcnet_exp.summarize_runs --runs-root .\runs --output .\runs\summary.csv
```

## Notes

- The current models are intentionally lightweight placeholders so we can make the training pipeline reproducible before we swap in the final JDCNET architecture.
- All experiments save outputs under `runs/<experiment_name>/`.
- Paper-ready summary figures are exported to `paper/images/generated/`, and tabulated summaries are exported to `paper/results/`.
- Training now exports `history.json`, `history.csv`, `learning_curves.png`, `best_metrics.json`, and `confusion_matrix.png` for each run.
