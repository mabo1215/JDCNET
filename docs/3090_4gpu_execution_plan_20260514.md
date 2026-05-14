# 3090 Four-GPU Execution Plan for Fast GAP-KD Validation Screens (2026-05-14)

## Scope

This document is the local execution plan for the four-card RTX 3090 remote host:

```text
ssh mabo1215@10.147.20.176
repo: /data/JDCNET/src or /home1/mabo1215/JDCNET
experiment/data root: /data1/midrc and /data/bimcv
```

Do **not** use this plan for the H800 no-card remote. H800 remains reserved for the 559-case locked MIDRC validation after GPU/card mode is restored.

The goal here is to use the 4 x 3090 machine as an aggressive screening engine: saturate all four GPUs with independent single-GPU jobs, maximize per-GPU batch size and loader throughput, finish the most informative experiments quickly, and produce analyzable CSV/JSON summaries that decide whether any variant is worth promoting to H800 locked validation later.

## Scientific starting point

The current evidence boundary is:

- The locked MIDRC candidate did not validate: CT teacher BA is weak and reliability-gated KD is not stably above supervised or plain KD.
- Projection attention has not helped; the conservative candidate is gating-only with `projected_attention_weight=0.0`.
- The validation gate remains strict: mean Delta BA must be positive by at least `+0.03`, Macro-F1 must move in the same direction, specificity must not collapse, and the lower 95% CI should be above zero before any validated-architecture claim.
- 3090 does not have MIDRC raw CT ZIPs, so it cannot run new raw-CT multi-window teacher generation. It does have BIMCV DRR / X-ray assets and MIDRC projected-image assets.

Therefore, the 3090 plan is not a final validation claim. It is a fast same-source paired screening campaign. If it fails, keep the evidence-bounded negative framing. If it succeeds, use it as a positive pilot and as a candidate selector for later H800/MIDRC validation.

## Available 3090 assets assumed

```text
/data/bimcv/drr_cache/bimcv_S{patient}.png
/data1/midrc/bimcv_xray_256/
/data1/midrc/teacher_variants_20260514/images/ct_mean_projection_lung/
/data1/midrc/5fold_cv_20260514/
/data1/logs/midrc_5fold_cv_3090/
```

Expected BIMCV paired cohort:

```text
BIMCV patients: 510 total
COVID-positive: 114
COVID-negative: 396
paired X-ray + same-patient DRR teacher available
```

## Priority order

### Priority 1: BIMCV-only 5-fold CV, four-row matrix

This is the highest-value experiment on the 3090 because BIMCV DRR teacher and BIMCV X-ray are same-source and same-patient paired. It removes the MIDRC-to-BIMCV and CT-projection domain-shift confound.

Run two versions if time permits:

1. **Balanced BIMCV-only CV**
   - Select all 114 positive patients.
   - Seeded sample 114 negative patients.
   - Total: 228 patients.
   - Five folds: approximately 22-23 positive and 22-23 negative test patients per fold.
   - Out-of-fold pooled evaluation: 114 positive and 114 negative patients.

2. **Full BIMCV-only CV**
   - Keep all 510 patients.
   - Five folds: approximately 102 patients per fold, imbalanced but larger.
   - Use balanced accuracy, AUROC, Macro-F1, specificity, and class-stratified fold reports.

Four-row matrix per fold and seed:

| Row | Method | Purpose |
| --- | --- | --- |
| 1 | DRR/CT teacher | Establish same-source teacher upper bound |
| 2 | X-ray supervised | Deployment baseline |
| 3 | Plain CT-logit KD | Simple transfer baseline |
| 4 | Reliability-gated KD | Locked candidate, `threshold=0.55`, `projection=0.0` |

Recommended initial seeds:

```text
SEEDS="42 43 44 45 46 47"
FOLDS=5
METHODS=4
TOTAL_RUNS=5 * 6 * 4 = 120 runs
```

To finish faster, run staged:

```text
Stage A1 smoke: folds 0-1, seeds 42-43, four rows = 16 runs
Stage A2 decision screen: all 5 folds, seeds 42-44 = 60 runs
Stage A3 stability extension: all 5 folds, seeds 45-47 = 60 additional runs
```

### Priority 2: Temperature and entropy/margin gate scan

Only run this after Priority 1 has confirmed that the DRR teacher beats supervised in most folds. Otherwise calibration cannot rescue a bad teacher.

Small grid:

```text
TEMPERATURES="2 4 8"
GATE_THRESHOLDS="0.50 0.55 0.60"
MAX_ENTROPY="-1.0 0.60"   # -1 disables entropy gate
MIN_MARGIN="0.0 0.10"
PROJECTION=0.0 only
SEEDS="42 43 44"
```

First-pass reduced grid to avoid wasting time:

```text
T in {2,4,8}
threshold in {0.50,0.55,0.60}
entropy disabled
margin 0
folds 0-4, seeds 42-44
```

Primary diagnostic is not only BA but also:

```text
history.csv: kd_gate_active_fraction
history.csv: kd_gate_mean_weight
history.csv: teacher_train_accuracy
history.csv: teacher_train_mean_confidence
```

A useful calibration candidate should increase gate-active fraction without lowering fold-level teacher correctness.

### Priority 3: MIDRC-only warmup/longer-epoch repeat

Run only after BIMCV-only is queued or complete. It is useful as an appendix stability check, not as main validation, because fold test size remains too small.

Configuration:

```text
EPOCHS=50
validation_interval=1
projection=0.0
gate_threshold=0.55
SEEDS="42 43 44 45 46 47"
FOLDS=5
```

If warmup code is not implemented yet, use longer epochs and AMP/channels-last first; do not block Priority 1 on warmup implementation.

## GPU utilization strategy

Use four independent single-GPU workers, not one multi-GPU process. The experiments are small and numerous; queue-level parallelism gives better utilization and simpler recovery.

```text
GPU0: sequential queue shard 0
GPU1: sequential queue shard 1
GPU2: sequential queue shard 2
GPU3: sequential queue shard 3
```

Each queue should skip completed runs by checking:

```bash
[ -s "$RUN_DIR/best_metrics.json" ] && [ -s "$RUN_DIR/best.pt" ]
```

Use `screen` sessions:

```text
bimcv5f_g0
bimcv5f_g1
bimcv5f_g2
bimcv5f_g3
bimcv5f_watch
```

## Throughput tuning before the main run

The prior synthetic 3090 probe suggested very large batch sizes can fit, but real paired-image training has more I/O pressure. Do not blindly set batch=1024 for all experiments. Run a 10-20 minute throughput sweep and then lock the fastest stable setting.

Test grid:

```text
BATCH_SIZE candidates: 64, 128, 256, 512
NUM_WORKERS candidates: 8, 12, 16, 24, 32
PREFETCH_FACTOR: 2 or 4
PERSISTENT_WORKERS: true
PIN_MEMORY: true
AMP: true
CHANNELS_LAST: true
TORCH_COMPILE: true for final runs, false for one-epoch probe if compile overhead dominates
```

Selection rule:

1. Reject any OOM or loader crash.
2. Reject configs where CPU load or disk I/O stalls cause GPU utilization below 60% after warmup.
3. Prefer the largest batch size that keeps per-GPU memory under about 22 GiB and does not slow wall-clock per epoch.
4. If all high-batch configs tie, choose the smaller one to reduce failure risk.

Likely starting settings for ResNet18 224 paired-image KD on 24GB 3090:

```text
Teacher / supervised rows: BATCH_SIZE=256, NUM_WORKERS=16
Plain KD / gated KD rows: BATCH_SIZE=128 or 256, NUM_WORKERS=16
Fallback safe setting: BATCH_SIZE=64, NUM_WORKERS=8
```

Use these config fields:

```json
"data": {
  "batch_size": 128,
  "num_workers": 16,
  "pin_memory": true,
  "persistent_workers": true,
  "prefetch_factor": 4,
  "use_weighted_sampler": true
},
"optimization": {
  "amp": true,
  "channels_last": true,
  "torch_compile": true,
  "grad_accum_steps": 1,
  "validation_interval": 1
}
```

## Required local code/script additions before execution

The current repository already has generic training, evaluation, and mixed-CV utilities. For a clean BIMCV-only run, add one dedicated 3090 script rather than overloading H800/MIDRC scripts.

Recommended new files:

```text
src/jdcnet_exp/prepare_bimcv_only_cv.py
src/ops/remote_3090_bimcv_only_5fold_cv.sh
src/ops/remote_3090_bimcv_only_5fold_summarize.sh
src/ops/debug/check_3090_bimcv_only_status.sh
```

### `prepare_bimcv_only_cv.py` responsibilities

Input:

```text
--bimcv-manifest /data/JDCNET/src/data/bimcv/bimcv_for_mixed_cv.csv
--output-dir /data1/midrc/bimcv_only_cv_20260514
--prefix bimcv_only
--folds 5
--seed 99
--mode balanced | full
--require-existing-paths
```

Output per fold:

```text
fold_00/bimcv_only_fold00_paired_manifest.csv
fold_00/bimcv_only_fold00_ct_manifest.csv
...
bimcv_only_patient_index.csv
bimcv_only_summary.json
```

Implementation requirements:

- Patient-level split only.
- Stratify by label.
- In balanced mode, keep all positives and sample equal negatives by seed.
- In full mode, keep all patients and report imbalance.
- `paired_manifest`: X-ray student path in `image_path`, DRR teacher path in `teacher_image_path`, modality `xray`.
- `ct_manifest`: copy of the same rows but swap `image_path = teacher_image_path`, modality `ct`.
- Include path-existence filtering and counts in JSON summary.

### `remote_3090_bimcv_only_5fold_cv.sh` responsibilities

Environment knobs:

```bash
ROOT=${ROOT:-/data/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
BIMCV_MANIFEST=${BIMCV_MANIFEST:-$ROOT/data/bimcv/bimcv_for_mixed_cv.csv}
CV_DIR=${CV_DIR:-/data1/midrc/bimcv_only_cv_20260514}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/bimcv_only_5fold_cv}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/bimcv_only_5fold_cv}
LOG_DIR=${LOG_DIR:-/data1/logs/bimcv_only_5fold_cv_3090}
SEEDS=${SEEDS:-"42 43 44"}
FOLDS=${FOLDS:-"0 1 2 3 4"}
MODE=${MODE:-balanced}
EPOCHS=${EPOCHS:-50}
TEACHER_EPOCHS=${TEACHER_EPOCHS:-30}
BATCH_SIZE=${BATCH_SIZE:-128}
NUM_WORKERS=${NUM_WORKERS:-16}
PREFETCH_FACTOR=${PREFETCH_FACTOR:-4}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-true}
GATE_THRESHOLD=${GATE_THRESHOLD:-0.55}
TEMPERATURE=${TEMPERATURE:-4.0}
ALPHA=${ALPHA:-0.6}
```

Generated configs per fold/seed:

```text
bimcv_only_f{fold}_teacher_drr_s{seed}.json
bimcv_only_f{fold}_xray_supervised_s{seed}.json
bimcv_only_f{fold}_plain_kd_s{seed}.json
bimcv_only_f{fold}_gated_kd_thr055_proj0000_s{seed}.json
```

Teacher configs use:

```json
"train_modalities": ["ct"],
"val_modalities": ["ct"],
"manifest_path": "..._ct_manifest.csv"
```

Student/KD configs use:

```json
"train_modalities": ["xray"],
"val_modalities": ["xray"],
"manifest_path": "..._paired_manifest.csv",
"paired_image_column": "teacher_image_path"
```

For final test evaluation, generate a temporary evaluation config per run with:

```json
"val_split": "test"
```

and run:

```bash
python3 -m jdcnet_exp.evaluate \
  --config "$TEST_CFG" \
  --checkpoint "$RUN_DIR/best.pt" \
  --output-dir "$RUN_DIR/test_eval"
```

This avoids confusing validation checkpoint selection with fold-test reporting.

## Launch commands

### 1. Sync code and enter repo on 3090

```bash
ssh mabo1215@10.147.20.176
cd /data/JDCNET/src
# If GitHub pull is available:
git pull --ff-only origin main
# If GitHub is blocked, use the local bundle sync workflow from Windows.
```

### 2. Pre-flight status

```bash
nvidia-smi
screen -ls
 df -h /data /data1 /home1
python3 - <<'PY'
import torch
print(torch.__version__)
print(torch.cuda.is_available(), torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i))
PY
```

### 3. Throughput probe

Run the probe first with a restricted fold/seed set:

```bash
ROOT=/data/JDCNET/src \
MODE=balanced \
FOLDS="0" \
SEEDS="42" \
EPOCHS=2 \
TEACHER_EPOCHS=2 \
BATCH_SIZE=128 \
NUM_WORKERS=16 \
PREFETCH_FACTOR=4 \
AMP=true CHANNELS_LAST=true TORCH_COMPILE=false \
bash src/ops/remote_3090_bimcv_only_5fold_cv.sh
```

Repeat for `BATCH_SIZE=64/128/256/512` and `NUM_WORKERS=8/16/24/32`, assigning one candidate per GPU if the script supports a probe queue.

### 4. Main balanced run

```bash
ROOT=/data/JDCNET/src \
MODE=balanced \
FOLDS="0 1 2 3 4" \
SEEDS="42 43 44" \
EPOCHS=50 \
TEACHER_EPOCHS=30 \
BATCH_SIZE=128 \
NUM_WORKERS=16 \
PREFETCH_FACTOR=4 \
AMP=true CHANNELS_LAST=true TORCH_COMPILE=true \
GATE_THRESHOLD=0.55 \
TEMPERATURE=4.0 \
ALPHA=0.6 \
bash src/ops/remote_3090_bimcv_only_5fold_cv.sh
```

If the first 60-run decision screen is positive, extend seeds:

```bash
SEEDS="45 46 47" bash src/ops/remote_3090_bimcv_only_5fold_cv.sh
```

### 5. Full imbalanced run, optional

```bash
MODE=full \
FOLDS="0 1 2 3 4" \
SEEDS="42 43 44" \
EPOCHS=50 \
TEACHER_EPOCHS=30 \
BATCH_SIZE=128 \
NUM_WORKERS=16 \
bash src/ops/remote_3090_bimcv_only_5fold_cv.sh
```

## Monitoring

```bash
screen -ls | grep bimcv5f
watch -n 30 'nvidia-smi; echo; tail -n 20 /data1/logs/bimcv_only_5fold_cv_3090/status.tsv'
```

Per-GPU logs:

```bash
tail -f /data1/logs/bimcv_only_5fold_cv_3090/gpu0_queue.log
tail -f /data1/logs/bimcv_only_5fold_cv_3090/gpu1_queue.log
tail -f /data1/logs/bimcv_only_5fold_cv_3090/gpu2_queue.log
tail -f /data1/logs/bimcv_only_5fold_cv_3090/gpu3_queue.log
```

Failure triage:

```bash
grep -R "CUDA out of memory\|Traceback\|FileNotFoundError\|Killed" /data1/logs/bimcv_only_5fold_cv_3090 | tail -n 50
```

If OOM occurs, reduce only the failing row type first:

```text
KD rows: 128 -> 64
teacher/supervised rows: 256 -> 128
NUM_WORKERS: 24/32 -> 16 -> 8 if RAM/process pressure appears
```

## Summarization and decision outputs

`remote_3090_bimcv_only_5fold_summarize.sh` should write:

```text
/data1/logs/bimcv_only_5fold_cv_3090/summary_by_run.csv
/data1/logs/bimcv_only_5fold_cv_3090/summary_by_fold_seed.csv
/data1/logs/bimcv_only_5fold_cv_3090/delta_summary.csv
/data1/logs/bimcv_only_5fold_cv_3090/oof_pooled_metrics.json
/data1/logs/bimcv_only_5fold_cv_3090/decision_report.md
```

Minimum columns:

```text
mode, fold, seed, method, split, n_pos, n_neg,
balanced_accuracy, macro_f1, specificity, sensitivity, mcc, auroc,
teacher_ba, supervised_ba, plain_kd_ba, gated_kd_ba,
delta_gated_vs_supervised_ba, delta_gated_vs_plain_ba,
kd_gate_active_fraction_last, kd_gate_mean_weight_last,
teacher_train_accuracy_last, teacher_train_mean_confidence_last
```

Decision checks for BIMCV-only pilot:

1. DRR teacher beats X-ray supervised in most fold/seed pairs.
2. Gated KD beats supervised and plain KD in most fold/seed pairs.
3. Mean Delta BA vs both baselines is at least `+0.03`.
4. Bootstrap 95% CI lower bound for Delta BA is above zero on out-of-fold pooled predictions, or at least above zero for seed-paired fold deltas.
5. Macro-F1 direction matches BA.
6. Specificity does not collapse.

Interpretation:

- If all pass on balanced and are directionally consistent on full BIMCV, write as a same-source positive pilot, not final validation.
- If only teacher passes but KD fails, focus next on calibration and gate diagnostics.
- If teacher also fails, stop 3090 KD escalation and preserve evidence-bounded negative framing.

## Result pullback to local repo

After summarization:

```powershell
# From Windows local repo root
scp -r mabo1215@10.147.20.176:/data1/logs/bimcv_only_5fold_cv_3090 docs/tmp/3090_bimcv_only_5fold_cv_20260514
```

Then commit only compact results:

```text
Keep: CSV summaries, JSON summaries, decision_report.md, selected logs.
Do not commit: checkpoints, large run directories, raw images, full tensor artifacts.
```

## Time budget

Expected rough wall-clock on 4 x RTX 3090 after throughput tuning:

```text
Throughput probe: 10-30 min
Stage A1 smoke: <30 min
Stage A2 60-run balanced screen: ~2-4 h depending on batch/worker setting
Stage A3 additional seeds: ~2-4 h
Temperature scan: ~2-6 h if restricted to promising folds/seeds
```

## Stop conditions

Stop early and summarize if any of these occurs:

1. DRR teacher is not above supervised in at least 60% of fold/seed pairs.
2. Gated KD has mean Delta BA <= 0 after the first 3 seeds x 5 folds.
3. Gate-active fraction is near zero across most runs.
4. Specificity collapses relative to supervised.
5. I/O bottleneck prevents stable GPU utilization even after lowering workers and batch size.

## Recommended immediate next action

Implement the three 3090 BIMCV-only helper scripts, push to GitHub, pull/sync on `10.147.20.176`, run the throughput probe, then launch the balanced 5-fold four-row matrix with all four GPUs saturated.
