#!/usr/bin/env bash
set -euo pipefail
# A4: external X-ray-only validation of the FROZEN deployed students (no retraining).
#
# Evaluates the supervised X-ray baseline and the two gate-passing JDCNet students,
# trained on the 510-patient BIMCV cohort, on an INDEPENDENT external X-ray manifest
# (e.g. a MIDRC / public COVID CXR cohort) and reports absolute metrics under domain
# shift. Inference only: each run just loads best.pt and scores the external split.
#
# PREREQUISITE: an external X-ray manifest CSV with columns
#   image_path,label,modality,split,patient_id
# where rows for evaluation have modality=xray and split=${EXT_SPLIT}. Build it first,
# e.g.:  python3 -m jdcnet_exp.prepare_midrc_dataset --out /data1/external/midrc   (see that
# module's --help), then point EXT_MANIFEST at the resulting xray manifest.

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
EXT_TAG=${EXT_TAG:-midrc_external}
EXT_MANIFEST=${EXT_MANIFEST:-/data1/external/midrc/midrc_xray_manifest.csv}
EXT_SPLIT=${EXT_SPLIT:-test}
SOURCE_TAG=${SOURCE_TAG:-bimcv_full_paired_cv_20260516}
SUP_RUN_ROOT=${SUP_RUN_ROOT:-/data1/midrc/runs/${SOURCE_TAG}}
# Checkpoint groups to evaluate: "label=<glob of run dirs containing best.pt>".
# Defaults: supervised baseline + the two passing JDCNet cells (override as needed
# to match the exact run tags on disk, e.g. the lam15 / soft extension sweeps).
CKPT_SPECS=${CKPT_SPECS:-"\
supervised=${SUP_RUN_ROOT}/*_supervised \
jdcnet_3slice_softkl=/data1/midrc/runs/bimcv_pseudolabel_soft_20260516/3slice_*_t070_l100 \
jdcnet_mid_hard=/data1/midrc/runs/bimcv_pseudolabel_lam15_20260516/mid_*_t080_l150"}
OUT_ROOT=${OUT_ROOT:-/data1/midrc/runs/${EXT_TAG}_eval}
LOG_DIR=${LOG_DIR:-/data1/logs/${EXT_TAG}_eval}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${EXT_TAG}_eval}
INPUT_SIZE=${INPUT_SIZE:-224}
BATCH_SIZE=${BATCH_SIZE:-128}
NUM_WORKERS=${NUM_WORKERS:-8}
GPUS=${GPUS:-"0 1 2 3"}
MODEL_NAME=${MODEL_NAME:-student}
MODEL_BACKBONE=${MODEL_BACKBONE:-resnet18}
DRY_RUN=${DRY_RUN:-false}

mkdir -p "$OUT_ROOT" "$LOG_DIR" "$CONFIG_DIR"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
cd "$ROOT"

if [ ! -s "$EXT_MANIFEST" ]; then
  log "ERROR external manifest not found: $EXT_MANIFEST (build it first; see header)"
  exit 1
fi
log "EXTERNAL_EVAL_START tag=$EXT_TAG manifest=$EXT_MANIFEST split=$EXT_SPLIT"

# Build one eval config per checkpoint, collect (gpu-round-robin) job list.
JOBS="$LOG_DIR/jobs.tsv"; : > "$JOBS"
export EXT_MANIFEST EXT_SPLIT INPUT_SIZE BATCH_SIZE NUM_WORKERS CONFIG_DIR OUT_ROOT MODEL_NAME MODEL_BACKBONE
gi=0
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
    'model': {'name': os.environ['MODEL_NAME'], 'num_classes': 2, 'input_size': int(os.environ['INPUT_SIZE']),
              'use_dpe': False, 'use_mhra': False, 'use_dfpn': False,
              'paired_input': False, 'backbone': os.environ['MODEL_BACKBONE']},
    'data': {'train_split': 'train', 'val_split': os.environ['EXT_SPLIT'],
             'train_modalities': ['xray'], 'val_modalities': ['xray'],
             'batch_size': int(os.environ['BATCH_SIZE']), 'num_workers': int(os.environ['NUM_WORKERS']),
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
[ "$N" -eq 0 ] && { log "no checkpoints matched; check CKPT_SPECS globs"; exit 1; }

if [ "$DRY_RUN" = "true" ]; then
  log "DRY_RUN configs/jobs only; not running evaluation"
  exit 0
fi

mapfile -t gpus < <(printf '%s\n' $GPUS)
i=0
while IFS=$'\t' read -r cfg ckpt outdir; do
  gpu="${gpus[$((i % ${#gpus[@]}))]}"; i=$((i+1))
  name="$(basename "$outdir")"
  if [ -s "$outdir/metrics.json" ]; then log "SKIP_DONE $name"; continue; fi
  (
    CUDA_VISIBLE_DEVICES="$gpu" "$PYTHON_BIN" -m jdcnet_exp.evaluate \
      --config "$cfg" --checkpoint "$ckpt" --output-dir "$outdir" > "$LOG_DIR/${name}.log" 2>&1 \
      && log "DONE gpu=$gpu $name" || log "FAIL gpu=$gpu $name"
  ) &
  # cap concurrency at #gpus
  if [ $((i % ${#gpus[@]})) -eq 0 ]; then wait; fi
done < "$JOBS"
wait
log "EXTERNAL_EVAL_DONE tag=$EXT_TAG"

# Summarize absolute metrics per checkpoint group (mean +/- sd).
"$PYTHON_BIN" - "$OUT_ROOT" "$LOG_DIR/external_summary.csv" <<'PY'
import csv, json, re, sys
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
