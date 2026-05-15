# C2 BiomedCLIP Fine-Tune CV Decision Report

Generated on 2026-05-15 UTC from `/data1/midrc/runs/bimcv_biomedclip_cv_20260516`.


## Run completion

- Completed test metrics: 15/15.

- Execution: 2x RTX 3090 (GPU2/3), batch_size=64, num_workers=8, full visual-tower fine-tune, lr=1e-5, 50 epochs.


## Mean test metrics

| Baseline | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| biomedclip_ft | 15 | 0.6333 [0.6007, 0.6658] | 0.6298 | 0.5960 | 0.6631 |
| c1_resnet18_supervised_mean_same226 | 15 | 0.6311 [0.6073, 0.6558] | 0.6217 | 0.6389 | 0.6900 |
| previous_bimcv_only_xray_supervised_228 | 15 | 0.5657 [0.5310, 0.6001] | 0.5358 | 0.5057 | 0.6208 |

## Paired deltas

| Comparison | n | Delta BA mean [95% CI] | +/-/0 | Delta F1 | Delta Spec | Pass |
|---|---:|---:|---:|---:|---:|---:|
| vs_c1_resnet18_supervised_same226 | 15 | 0.0022 [-0.0476, 0.0496] | 8/7/0 | 0.0080 | -0.0429 | NO |
| vs_previous_bimcv_only_supervised_228 | 15 | 0.0675 [0.0213, 0.1119] | 12/3/0 | 0.0940 | 0.0904 | YES |

## Decision

- BiomedCLIP fine-tune exceeds at least one ResNet18 supervised baseline under the +0.03 / CI>0 gate.


Raw CSVs: `biomedclip_summary.csv`, `biomedclip_deltas.csv`.
