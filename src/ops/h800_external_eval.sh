#!/usr/bin/env bash
set -euo pipefail
# H800: A4 — external X-ray-only validation of FROZEN deployed students.
#
# Evaluates supervised X-ray baseline and gate-passing JDCNet students
# (trained on the BIMCV cohort) on an INDEPENDENT external X-ray manifest.
# Inference only — no retraining.
#
# PREREQUISITE:
#   1. An external X-ray manifest CSV with columns:
#        image_path,label,modality,split,patient_id
#      where rows have modality=xray and split=$EXT_SPLIT.
#      Build it with:  python3 -m jdcnet_exp.prepare_midrc_dataset --out <dir>
#      or supply any external COVID CXR dataset manifest.
#   2. Trained checkpoints from h800_bimcv_5fold_cv.sh (supervised + KD students).
#
# Usage:
#   DRY_RUN=true bash h800_external_eval.sh   # generate configs only
#   bash h800_external_eval.sh                 # full evaluation

# ---------- paths ----------
ROOT=${ROOT:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}

EXT_TAG=${EXT_TAG:-h800_external_eval}
EXT_MANIFEST=${EXT_MANIFEST:-/root/autodl-tmp/data/external/midrc_xray_manifest.csv}
EXT_SPLIT=${EXT_SPLIT:-test}

SOURCE_TAG=${SOURCE_TAG:-bimcv_h800_5fold_cv}
SUP_RUN_ROOT=${SUP_RUN_ROOT:-/root/autodl-tmp/runs/${SOURCE_TAG}}

# Checkpoint groups to evaluate: "label=<glob of run dirs containing best.pt>".
# Default: supervised baselines + the two passing JDCNet cells from the calibrated gate.
CALIB_TAG=${CALIB_TAG:-bimcv_h800_calibrated_gate}
CKPT_SPECS=${CKPT_SPECS:-"\
supervised=${SUP_RUN_ROOT}/*_supervised \
jdcnet_3slice_softkl=/root/autodl-tmp/runs/${CALIB_TAG}/3slice_soft_*_T100 \
jdcnet_mid_hard=/root/autodl-tmp/runs/${CALIB_TAG}/mid_hard_*_T100"}

OUT_ROOT=${OUT_ROOT:-/root/autodl-tmp/runs/${EXT_TAG}}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/${EXT_TAG}}
CONFIG_DIR=${CONFIG_DIR:-${ROOT}/configs/${EXT_TAG}}

INPUT_SIZE=${INPUT_SIZE:-224}
BATCH_SIZE=${BATCH_SIZE:-128}
NUM_WORKERS=${NUM_WORKERS:-8}
GPU_ID=${GPU_ID:-0}
MAX_PARALLEL=${MAX_PARALLEL:-4}
MODEL_NAME=${MODEL_NAME:-student}
MODEL_BACKBONE=${MODEL_BACKBONE:-resnet18}
DRY_RUN=${DRY_RUN:-false}

mkdir -p "$OUT_ROOT" "$LOG_DIR" "$CONFIG_DIR"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
cd "$ROOT"

if [ ! -s "$EXT_MANIFEST" ]; then
  log "ERROR external manifest not found: $EXT_MANIFEST"
  echo "Build it first, e.g.:  $PYTHON_BIN -m jdcnet_exp.prepare_midrc_dataset --out /root/autodl-tmp/data/external"
  exit 1
fi
log "EXTERNAL_EVAL_START tag=$EXT_TAG manifest=$EXT_MANIFEST split=$EXT_SPLIT"

# Build one eval config per checkpoint.
JOBS="$LOG_DIR/jobs.tsv"; : > "$JOBS"
export EXT_MANIFEST EXT_SPLIT INPUT_SIZE BATCH_SIZE NUM_WORKERS CONFIG_DIR OUT_ROOT MODEL_NAME MODEL_BACKBONE

for spec in $CKPT_SPECS; do
  label="${spec%%=*}"; glob="${spec#*=}"
  found=0
  for run_dir in $glob; do
    ckpt="$run_dir/best.pt"
    [ -s "$ckpt" ] || continue
    found=$((found+1))
    runname="${label}__$(basename "$run_dir")"
    cfg="$CONFIG_DIR/${runname}.json"
    "$PYTHON_BIN" - "$cfg" "$runname" <<'PY'
import json, os, sys
cfg_path, runname = sys.argv[1], sys.argv[2]
cfg = {
    'experiment_name': runname,
    'manifest_path': os.environ['EXT_MANIFEST'],
    'output_dir': os.path.join(os.environ['OUT_ROOT'], runname),
    'seed': 42,
    'model': {'name': os.environ['MODEL_NAME'], 'num_classes': 2,
              'input_size': int(os.environ['INPUT_SIZE']),
              'use_dpe': False, 'use_mhra': False, 'use_dfpn': False,
              'paired_input': False, 'backbone': os.environ['MODEL_BACKBONE']},
    'data': {'train_split': 'train', 'val_split': os.environ['EXT_SPLIT'],
             'train_modalities': ['xray'], 'val_modalities': ['xray'],
             'batch_size': int(os.environ['BATCH_SIZE']),
             'num_workers': int(os.environ['NUM_WORKERS']),
             'use_weighted_sampler': False, 'pin_memory': True},
    'optimization': {'epochs': 1, 'learning_rate': 3e-4, 'weight_decay': 1e-4, 'amp': True},
    'distillation': {'enabled': False},
}
json.dump(cfg, open(cfg_path, 'w'), indent=2)
PY
    printf '%s\t%s\t%s\n' "$cfg" "$ckpt" "$OUT_ROOT/$runname" >> "$JOBS"
  done
  log "GROUP $label matched=$found ($glob)"
done

N=$(wc -l < "$JOBS")
log "EVAL_JOBS=$N"
[ "$N" -eq 0 ] && { log "No checkpoints matched; check CKPT_SPECS globs"; exit 1; }

if [ "$DRY_RUN" = "true" ]; then
  log "DRY_RUN configs/jobs only; not running evaluation"
  exit 0
fi

# Launch evaluation with concurrency cap.
i=0
while IFS=$'\t' read -r cfg ckpt outdir; do
  name="$(basename "$outdir")"
  if [ -s "$outdir/metrics.json" ]; then log "SKIP_DONE $name"; continue; fi
  (
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PYTHON_BIN" -m jdcnet_exp.evaluate \
      --config "$cfg" --checkpoint "$ckpt" --output-dir "$outdir" > "$LOG_DIR/${name}.log" 2>&1 \
      && log "DONE gpu=$GPU_ID $name" || log "FAIL gpu=$GPU_ID $name"
  ) &
  i=$((i+1))
  if [ $((i % MAX_PARALLEL)) -eq 0 ]; then wait; fi
done < "$JOBS"
wait
log "EXTERNAL_EVAL_DONE tag=$EXT_TAG"

# Summarize absolute metrics per group (mean +/- sd).
"$PYTHON_BIN" - "$OUT_ROOT" "$LOG_DIR/external_summary.csv" <<'PY'
import csv, json, sys
from pathlib import Path
import statistics as st
out_root = Path(sys.argv[1]); summary = Path(sys.argv[2])
rows = {}
for m in out_root.glob('*/metrics.json'):
    name = m.parent.name
    group = name.split('__', 1)[0]
    d = json.loads(m.read_text())
    rows.setdefault(group, []).append(d)
keys = ['balanced_accuracy', 'roc_auc', 'macro_f1', 'sensitivity', 'specificity', 'accuracy']
with open(summary, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['group', 'n'] + [f'{k}_mean' for k in keys] + [f'{k}_sd' for k in keys])
    for g, ds in sorted(rows.items()):
        means, sds = [], []
        for k in keys:
            vals = [float(x[k]) for x in ds if k in x and x[k] is not None]
            means.append(round(st.mean(vals), 4) if vals else '')
            sds.append(round(st.pstdev(vals), 4) if len(vals) > 1 else 0.0 if vals else '')
        w.writerow([g, len(ds)] + means + sds)
print(summary.read_text())
PY
log "SUMMARY_WRITTEN $LOG_DIR/external_summary.csv"
