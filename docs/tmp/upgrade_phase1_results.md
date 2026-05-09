# JDCNet Upgrade — Phase 1 Diagnostic Ablation Results

Status: **in progress (launched 2026-05-09)**

Plan: `docs/tmp/jdcnet_upgrade_plan.md` Section 3.

## Question

Is the Custom-CNN supervised X-ray ceiling (~0.60 BA on 512-patient BIMCV) due
to backbone capacity or due to genuine data scarcity? Resolving this gates the
decision between Tier-A (small upgrade) and Tier-B (architectural rebuild).

## Setup

| Backbone   | Method              | Seeds       | Source                                |
|-----------|---------------------|-------------|---------------------------------------|
| Custom CNN| X-ray supervised    | 42, 43, 44  | reused — `r3090_bimcv_512` (existing) |
| ResNet-18 | X-ray supervised    | 42, 43      | new — `bimcv_phase1_diag/`            |

- Same manifest: `data/bimcv/bimcv_merged_paired_manifest.csv` (1251 rows /
  512 patients, train 318 neg / 91 pos, val 80 neg / 23 pos).
- Same optimizer / batch / epochs / weighted sampler.
- Both backbones use input_size=224, AdamW 3e-4, weight decay 1e-4, batch 16,
  50 epochs, balanced-accuracy best-checkpoint criterion.
- ResNet-18 weights: `IMAGENET1K_V1` (downloaded once, 11.7M params).

## Custom-CNN baseline (already on disk)

| Run                                     | Bal. accuracy | ROC-AUC |
|----------------------------------------|---------------|---------|
| `r3090_bimcv_512_xray_supervised_s42`  | 0.5819        | 0.6209  |
| `r3090_bimcv_512_xray_supervised_s43`  | 0.6056        | 0.5988  |
| `r3090_bimcv_512_xray_supervised_s44`  | 0.6043        | 0.6136  |
| **Mean (s42, s43)**                     | **0.5938**    | 0.6099  |

## ResNet-18 runs (4 GPUs)

| Run                                            | Status      | Best BA | ROC-AUC |
|-----------------------------------------------|-------------|---------|---------|
| `bimcv_phase1_diag/bimcv_resnet18_xray_supervised_s42` | running GPU0 (~ep23) | partial: 0.651 @ ep15 | 0.640 |
| `bimcv_phase1_diag/bimcv_resnet18_xray_supervised_s43` | running GPU1 (~ep23) | partial: 0.665 @ ep16 | 0.666 |
| `bimcv_phase1_diag/bimcv_resnet18_teacher_ct_s42`      | **done** | **0.6827** @ best | 0.6946 |
| `bimcv_phase1_diag/bimcv_resnet18_teacher_ct_s43`      | **done** | **0.7028** @ best | 0.6808 |

### Teacher-side observation

ResNet-18 CT teacher mean BA = **0.693**, custom-CNN CT teacher mean BA = **0.696**.
Backbone change does **not** improve the teacher under the current data
pipeline (single central CT slice). Final-epoch train loss for ResNet-18
teacher s42 hit 0.005 with val AUC declining from peak 0.71 (ep30) to 0.69
(ep50): clear overfitting on small CT support (~409 train slices).

Implication for Tier-A: keep custom-CNN teacher as default OR add early
stopping at epoch ~30 / smaller LR / stronger weight decay for ResNet-18
teacher. Best-checkpoint criterion already saves the peak; only matters if we
later want to compare teacher behavior across the full training trajectory.

### Supervised-side observation (partial, will update at completion)

ResNet-18 supervised X-ray partial mid-run best BA ≈ 0.658 (s42=0.651 @ep15,
s43=0.665 @ep16) versus custom-CNN supervised X-ray final mean BA ≈ 0.594.
ΔBA so far ≈ **+0.064**, above the 0.05 decision threshold even before the
runs finish. Final BA may rise further if epoch >25 produces a new best.

## H800 readiness (CPU mode, 2026-05-09)

H800 prepared so the moment GPU mode is enabled, training can start
immediately:

- Code aligned to `origin/main` (8538daa) on `https://github.com/mabo1215/JDCNET.git`.
  AutoDL `network_turbo` proxy lets the container reach GitHub.
- Python 3.12 / torch 2.8.0+cu128 / torchvision 0.23.0+cu128.
  ResNet-18 ImageNet weights pre-cached at
  `~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth`.
- 9 ResNet-18 configs uploaded to
  `/root/autodl-tmp/JDCNET/src/configs/bimcv_h800_headline/`:
  - `bimcv_h800_resnet18_xray_supervised_s{42,43,44}.json`
  - `bimcv_h800_resnet18_teacher_ct_s{42,43,44}.json` (epochs=30 to mitigate
    overfitting)
  - `bimcv_h800_resnet18_xray_cross_modal_kd_s{42,43,44}.json` (depends on
    teacher checkpoints from the second config family)
- Output and log dirs created: `/root/autodl-tmp/runs/bimcv_h800_phase1/`,
  `/root/autodl-tmp/logs/bimcv_h800_phase1/`.
- BIMCV manifest 1252 lines / 512 patients verified at
  `/root/autodl-tmp/data/bimcv/bimcv_merged_paired_manifest.csv`.
- CPU smoke test: see Section "Smoke test outcome" once it completes.

## Decision rules

- ΔBA = ResNet-18 mean − Custom-CNN mean over seeds {42, 43}.
- If ΔBA ≥ 0.05: backbone capacity is a real lever → proceed to Tier-A
  (multi-slice CT teacher + confidence-gated KD + symmetric KL on top of
  ResNet-18) and then Tier-B (DRR + multi-target + InfoNCE).
- If ΔBA in [0.03, 0.05): suggestive but not decisive → expand to seeds 44 and
  45 before deciding.
- If ΔBA < 0.03: backbone is not the limiting factor at this data scale; Tier-B
  becomes harder to justify scientifically. Falsifying our own assumption is
  also a useful outcome — the paper's evidence-bounded framing is then
  reinforced rather than overturned.

## Logs

- `/data/logs/bimcv_phase1_diag/resnet18_s42.log`
- `/data/logs/bimcv_phase1_diag/resnet18_s43.log`
- Outputs: `/data/JDCNET/src/runs/bimcv_phase1_diag/<name>/{best.pt,
  history.csv, best_metrics.json}`

## Next actions on completion

1. Pull `best_metrics.json` for both runs and update this table.
2. Compute ΔBA and apply the decision rule.
3. If proceed: open Tier-A code-change branch and update
   `docs/tmp/jdcnet_upgrade_plan.md` Section 6 status.
