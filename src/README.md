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
- paired-input late-fusion baseline support
- configurable DPE / MHRA / DFPN module switches
- patient-level Monte Carlo resampling with same-case mechanism controls
- run aggregation and paper-asset export
- Kaggle dataset download utility for auxiliary CT / MRI and COVID imaging datasets

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

Run the paired-cohort patient-level resampling study with attention-transfer and feature-hint mechanism controls:

```powershell
python -m jdcnet_exp.run_covid_resampling
```

Check whether a newly prepared paired manifest is ready for E1/M2/M10 training (no-GPU gate):

```powershell
python -m jdcnet_exp.data_readiness_gate --manifest .\data\bimcv\bimcv_combined_manifest.csv --dataset-name bimcv_combined --output .\results\bimcv_readiness_gate.json
```

Build one mixed BIMCV+MIDRC training index with train/val/test split, paired paths, and controllable positive ratio:

```powershell
python -m jdcnet_exp.prepare_mixed_bimcv_midrc_manifest \
	--bimcv-manifest .\data\bimcv\bimcv_paired_manifest.csv \
	--midrc-metadata-json .\data\midrc_manifests\MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.metadata.json \
	--midrc-root /data1/midrc/raw_559cases_combined \
	--output .\data\midrc_manifests\mixed_bimcv_midrc_manifest.csv \
	--split-output-dir .\data\midrc_manifests\mixed_bimcv_midrc_splits \
	--train-frac 0.7 --val-frac 0.1 --test-frac 0.2 \
	--target-train-positive-ratio 0.5 --sampling-mode upsample
```

The same settings can be edited in a JSON recipe and reused:

```powershell
Copy-Item .\configs\mixed_bimcv_midrc_manifest_recipe.example.json .\configs\mixed_bimcv_midrc_manifest_recipe.json
python -m jdcnet_exp.prepare_mixed_bimcv_midrc_manifest --recipe .\configs\mixed_bimcv_midrc_manifest_recipe.json
```

Notes:
- The mixed manifest keeps only path references and labels; images are loaded at training time by the dataloader.
- For MIDRC metadata input, each case is converted into one paired row: X-ray as image_path and CT as teacher_image_path.
- The output includes pairing columns (`pair_id`, `image_path`, `teacher_image_path`) and can also write separate `train.csv`, `val.csv`, and `test.csv` files.
- To keep natural validation/test prevalence, omit target-val-positive-ratio and target-test-positive-ratio.

Download curated Kaggle datasets into `src/data/kaggle/`:

```powershell
python -m jdcnet_exp.download_kaggle_datasets
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

- The current models remain lightweight research scaffolds; the late-fusion and module-ablation results are useful for revision, but they should not be mistaken for a final submission-grade JDCNet implementation.
- All experiments save outputs under `runs/<experiment_name>/`.
- Paper-ready summary figures are exported to `paper/images/generated/`, and tabulated summaries are exported to `paper/results/`.
- Training now exports `history.json`, `history.csv`, `learning_curves.png`, `best_metrics.json`, and `confusion_matrix.png` for each run.
