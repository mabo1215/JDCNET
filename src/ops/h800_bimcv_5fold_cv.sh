#!/usr/bin/env bash
set -euo pipefail
# H800 BIMCV 510-patient 5-fold cross-validation pipeline.
#
# Produces teacher + supervised + gated-KD checkpoints per (fold, seed),
# prerequisite for h800_calibrated_gate.sh (A2/A3) and h800_external_eval.sh (A4).
#
# Phase 1 (CPU, no GPU needed):
#   - Regenerate merged paired manifest (if neg data was re-downloaded)
#   - Generate 5-fold CV manifests via prepare_bimcv_only_cv.py
#   - Extract CT teacher variants (mid, 3slice, proj) from NIfTI volumes
#
# Phase 2 (GPU required):
#   - Train teachers per (variant, fold, seed)
#   - Train supervised X-ray baselines per (fold, seed)
#   - Train plain KD and gated KD per (fold, seed)
#   - Evaluate all on held-out test splits
#
# Usage:
#   # CPU-only prep (can run in no-GPU mode):
#   bash h800_bimcv_5fold_cv.sh --phase prep
#
#   # Full run (GPU mode):
#   bash h800_bimcv_5fold_cv.sh
#
# Teachers: mid + 3slice (the two variants whose cells pass the gate).
# 2 teachers x 5 folds x 3 seeds x 4 roles = 120 runs total.

# ---------- paths ----------
ROOT=${ROOT:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}

BIMCV_POS_DIR=${BIMCV_POS_DIR:-/root/autodl-tmp/data/bimcv_paired}
BIMCV_NEG_DIR=${BIMCV_NEG_DIR:-/root/autodl-tmp/data/bimcv_neg_paired}
BIMCV_MANIFEST=${BIMCV_MANIFEST:-/root/autodl-tmp/data/bimcv/bimcv_merged_paired_manifest.csv}

TAG=${TAG:-bimcv_h800_5fold_cv}
CV_DIR=${CV_DIR:-/root/autodl-tmp/bimcv_cv/${TAG}}
PREFIX=${PREFIX:-bimcv_full_paired}
RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-${ROOT}/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/${TAG}}
MANIFEST_DIR=${MANIFEST_DIR:-/root/autodl-tmp/bimcv_cv/${TAG}/manifests}

# CT variant output (persistent, not /dev/shm which is cleared on reboot)
CT_VARIANT_ROOT=${CT_VARIANT_ROOT:-/root/autodl-tmp/data/bimcv_ct_variants}
NIFTI_ROOTS=${NIFTI_ROOTS:-"$BIMCV_POS_DIR $BIMCV_NEG_DIR"}

# ---------- experiment grid ----------
TEACHERS=${TEACHERS:-"mid 3slice"}
FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
CV_SEED=${CV_SEED:-99}
CV_MODE=${CV_MODE:-balanced}

GPU_ID=${GPU_ID:-0}
MAX_PARALLEL=${MAX_PARALLEL:-8}
BATCH_SIZE=${BATCH_SIZE:-128}
TEACHER_BATCH_SIZE=${TEACHER_BATCH_SIZE:-${BATCH_SIZE}}
NUM_WORKERS=${NUM_WORKERS:-8}
PREFETCH_FACTOR=${PREFETCH_FACTOR:-4}
EPOCHS=${EPOCHS:-50}
TEACHER_EPOCHS=${TEACHER_EPOCHS:-30}
INPUT_SIZE=${INPUT_SIZE:-224}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-false}
USE_WEIGHTED_SAMPLER=${USE_WEIGHTED_SAMPLER:-true}

# KD params
ALPHA=${ALPHA:-0.6}
TEMPERATURE=${TEMPERATURE:-4.0}
THRESHOLD=${THRESHOLD:-0.55}

PHASE=${1:-all}  # "prep" for CPU-only, "train" for GPU-only, "all" for both

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR" "$MANIFEST_DIR" "$CT_VARIANT_ROOT"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
done_run(){ [ -s "$1/best.pt" ]; }

log "H800_5FOLD_START tag=$TAG phase=$PHASE teachers=[$TEACHERS] folds=[$FOLDS] seeds=[$SEEDS]"
cd "$ROOT"

# ============================
# PHASE 1: CPU-ONLY PREP
# ============================
if [ "$PHASE" = "prep" ] || [ "$PHASE" = "all" ]; then

  # Step 1a: Generate 5-fold CV manifests
  if [ ! -s "$CV_DIR/${PREFIX}_summary.json" ]; then
    log "PREPARE_CV_MANIFESTS"
    "$PYTHON_BIN" -u -m jdcnet_exp.prepare_bimcv_only_cv \
      --bimcv-manifest "$BIMCV_MANIFEST" \
      --output-dir "$CV_DIR" \
      --prefix "$PREFIX" \
      --folds 5 \
      --seed "$CV_SEED" \
      --mode "$CV_MODE" \
      > "$LOG_DIR/prepare_cv.log" 2>&1
    log "CV_MANIFESTS_DONE"
  else
    log "SKIP_PREPARE existing=$CV_DIR/${PREFIX}_summary.json"
  fi

  # Step 1b: Extract CT variants (mid, 3slice, proj) from NIfTI volumes
  log "EXTRACT_CT_VARIANTS roots=[$NIFTI_ROOTS]"
  "$PYTHON_BIN" -u ops/extract_ct_teacher_variants.py \
    --cv-dir "$CV_DIR" \
    --prefix "$PREFIX" \
    --roots $NIFTI_ROOTS \
    --drr-dir "$CT_VARIANT_ROOT/bimcv_ct_mid" \
    --out-root "$CT_VARIANT_ROOT" \
    --size "$INPUT_SIZE" \
    --summary "$LOG_DIR/extract_ct_variants.json" \
    > "$LOG_DIR/extract_ct_variants.log" 2>&1 || {
      log "WARN: CT variant extraction had errors; check $LOG_DIR/extract_ct_variants.json"
    }
  log "CT_VARIANTS_DONE"

  # Step 1c: Verify data readiness
  "$PYTHON_BIN" - "$CV_DIR" "$PREFIX" "$CT_VARIANT_ROOT" <<'PY'
import os, sys, json
from pathlib import Path

cv_dir, prefix, ct_root = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
issues = []

# Check fold manifests
for fold in range(5):
    for suffix in ['paired_manifest.csv', 'ct_manifest.csv']:
        p = cv_dir / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_{suffix}'
        if not p.exists():
            issues.append(f'Missing: {p}')

# Check CT variant dirs
for variant in ['bimcv_ct_mid', 'bimcv_ct_3slice', 'bimcv_ct_proj']:
    d = ct_root / variant
    if d.exists():
        n = len(list(d.glob('bimcv_S*.png')))
        print(f'  {variant}: {n} images')
    else:
        issues.append(f'Missing CT variant dir: {d}')

if issues:
    print(f'ISSUES ({len(issues)}):')
    for i in issues:
        print(f'  {i}')
else:
    print('All prerequisites OK')
PY
  log "PREP_PHASE_DONE"
fi

if [ "$PHASE" = "prep" ]; then
  log "CPU-ONLY PREP COMPLETE. Run with --phase train or no args for full run."
  exit 0
fi

# ============================
# PHASE 2: GPU TRAINING
# ============================
log "GENERATE_CONFIGS"

export ROOT TAG CV_DIR PREFIX RUN_ROOT CONFIG_DIR LOG_DIR MANIFEST_DIR CT_VARIANT_ROOT TEACHERS FOLDS SEEDS \
  BATCH_SIZE TEACHER_BATCH_SIZE NUM_WORKERS PREFETCH_FACTOR EPOCHS TEACHER_EPOCHS INPUT_SIZE AMP CHANNELS_LAST \
  TORCH_COMPILE USE_WEIGHTED_SAMPLER ALPHA TEMPERATURE THRESHOLD

"$PYTHON_BIN" - <<'PY'
import json, os
from pathlib import Path

run_root = Path(os.environ['RUN_ROOT']); cfg_dir = Path(os.environ['CONFIG_DIR'])
cv_dir = Path(os.environ['CV_DIR']); prefix = os.environ['PREFIX']
ct_root = Path(os.environ['CT_VARIANT_ROOT'])
teachers = os.environ['TEACHERS'].split()
folds = [int(x) for x in os.environ['FOLDS'].split()]
seeds = [int(x) for x in os.environ['SEEDS'].split()]
batch = int(os.environ['BATCH_SIZE']); tbatch = int(os.environ['TEACHER_BATCH_SIZE'])
workers = int(os.environ['NUM_WORKERS']); pf = int(os.environ['PREFETCH_FACTOR'])
epochs = int(os.environ['EPOCHS']); tepochs = int(os.environ['TEACHER_EPOCHS'])
isize = int(os.environ['INPUT_SIZE'])
amp = os.environ['AMP'].lower() == 'true'
chl = os.environ['CHANNELS_LAST'].lower() == 'true'
tc = os.environ['TORCH_COMPILE'].lower() == 'true'
ws = os.environ['USE_WEIGHTED_SAMPLER'].lower() == 'true'
alpha = float(os.environ['ALPHA']); temp = float(os.environ['TEMPERATURE']); thr = float(os.environ['THRESHOLD'])

variant_dirs = {
    'mid': ct_root / 'bimcv_ct_mid',
    '3slice': ct_root / 'bimcv_ct_3slice',
    'proj': ct_root / 'bimcv_ct_proj',
}

base_model = {'name': 'student', 'num_classes': 2, 'input_size': isize,
              'use_dpe': False, 'use_mhra': False, 'use_dfpn': False,
              'paired_input': False, 'backbone': 'resnet18'}

def data_cfg(bs, train_mod, val_mod):
    return {'train_split': 'train', 'val_split': 'val',
            'train_modalities': train_mod, 'val_modalities': val_mod,
            'batch_size': bs, 'num_workers': workers, 'paired_image_column': 'teacher_image_path',
            'use_weighted_sampler': ws, 'pin_memory': True,
            'persistent_workers': workers > 0, 'prefetch_factor': pf}

def optim_cfg(ep):
    return {'epochs': ep, 'learning_rate': 3e-4, 'weight_decay': 1e-4,
            'grad_accum_steps': 1, 'amp': amp, 'channels_last': chl,
            'torch_compile': tc, 'validation_interval': 1}

no_distill = {'enabled': False}

import re, pandas as pd

def patient_from_path(s):
    m = re.search(r'S\d+', str(s)); return m.group(0) if m else None

# Find common patients across all requested teacher variants
common = None
for t in teachers:
    avail = {patient_from_path(x.name) for x in variant_dirs[t].glob('bimcv_S*.png')}
    avail.discard(None)
    common = avail if common is None else common & avail
common = set(common or [])

man_dir = Path(os.environ['MANIFEST_DIR']); man_dir.mkdir(parents=True, exist_ok=True)

# Build teacher-variant-specific student manifests (rewrite teacher_image_path)
manifest_cache = {}
def student_manifest(t, fold):
    key = (t, fold)
    if key in manifest_cache: return manifest_cache[key]
    src = cv_dir / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_paired_manifest.csv'
    df = pd.read_csv(src)
    keep, vpaths = [], []
    for _, row in df.iterrows():
        pid = str(row['patient_id']).replace('bimcv_', '')
        ok = pid in common and Path(str(row['image_path'])).exists()
        keep.append(ok)
        vpaths.append(str(variant_dirs[t] / f'bimcv_{pid}.png') if ok else '')
    dfs = df[keep].copy().reset_index(drop=True)
    dfs['teacher_image_path'] = [p for p, k in zip(vpaths, keep) if k]
    out = man_dir / f'{t}_fold{fold:02d}_student_manifest.csv'
    dfs.to_csv(out, index=False)
    manifest_cache[key] = out
    return out

cfg_dir.mkdir(parents=True, exist_ok=True)
written = 0

for variant in teachers:
    for fold in folds:
        ct_manifest = str(cv_dir / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_ct_manifest.csv')
        paired_manifest = student_manifest(variant, fold)
        for seed in seeds:
            tag = f'{variant}_f{fold:02d}_s{seed}'
            # Teacher
            tname = f'{tag}_teacher'
            tdir = run_root / tname
            tcfg = {'experiment_name': tname, 'manifest_path': ct_manifest,
                    'output_dir': str(tdir), 'seed': seed,
                    'model': {**base_model, 'name': 'teacher'},
                    'data': data_cfg(tbatch, ['ct'], ['ct']),
                    'optimization': optim_cfg(tepochs), 'distillation': no_distill}
            (cfg_dir / f'{tname}.json').write_text(json.dumps(tcfg, indent=2))
            written += 1

            # Supervised
            sname = f'{tag}_supervised'
            scfg = {'experiment_name': sname, 'manifest_path': str(paired_manifest),
                    'output_dir': str(run_root / sname), 'seed': seed,
                    'model': base_model,
                    'data': data_cfg(batch, ['xray'], ['xray']),
                    'optimization': optim_cfg(epochs), 'distillation': no_distill}
            (cfg_dir / f'{sname}.json').write_text(json.dumps(scfg, indent=2))
            written += 1

            # Plain KD
            pkd = f'{tag}_plain_kd'
            pkdcfg = {**scfg, 'experiment_name': pkd, 'output_dir': str(run_root / pkd),
                      'distillation': {'enabled': True, 'temperature': temp, 'alpha': alpha,
                                       'teacher_checkpoint': str(tdir / 'best.pt')}}
            (cfg_dir / f'{pkd}.json').write_text(json.dumps(pkdcfg, indent=2))
            written += 1

            # Gated KD
            gname = f'{tag}_gated_kd_thr{int(round(thr*100)):03d}'
            gcfg = {**scfg, 'experiment_name': gname, 'output_dir': str(run_root / gname),
                    'distillation': {
                        'enabled': True, 'temperature': temp, 'alpha': alpha,
                        'teacher_checkpoint': str(tdir / 'best.pt'),
                        'confidence_gate_enabled': True,
                        'confidence_gate_threshold': thr,
                        'confidence_gate_floor': 0.0, 'confidence_gate_power': 1.0,
                        'confidence_gate_requires_correct': True,
                        'confidence_gate_positive_threshold': -1.0,
                        'confidence_gate_negative_threshold': -1.0,
                        'confidence_gate_min_margin': 0.0,
                        'confidence_gate_max_entropy': -1.0,
                        'projected_attention_weight': 0.0,
                    }}
            (cfg_dir / f'{gname}.json').write_text(json.dumps(gcfg, indent=2))
            written += 1

print(f'Wrote {written} configs to {cfg_dir}, common_patients={len(common)}')
PY

log "CONFIGS_GENERATED"

# Launch GPU training: single GPU, MAX_PARALLEL concurrent runs.
# Teachers must complete before KD variants that depend on them.
# Strategy: train all teachers first, then supervised, then KD variants.

for phase_label in teacher supervised plain_kd gated_kd; do
  log "PHASE: $phase_label"
  pending=()
  for cfg in "$CONFIG_DIR"/*_${phase_label}*.json; do
    [ -f "$cfg" ] || continue
    name=$(basename "$cfg" .json)
    run_dir="$RUN_ROOT/$name"
    if done_run "$run_dir"; then
      log "SKIP_DONE $name"
      continue
    fi
    pending+=("$cfg")
  done

  total=${#pending[@]}
  log "$phase_label: $total pending"
  [ "$total" -eq 0 ] && continue

  printf '%s\n' "${pending[@]}" | xargs -P "$MAX_PARALLEL" -I{} bash -c '
    cfg="$1"; name=$(basename "$cfg" .json)
    run_dir="'"$RUN_ROOT"'/$name"; log_f="'"$LOG_DIR"'/$name.log"
    printf "%s\tSTART gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
    CUDA_VISIBLE_DEVICES='"$GPU_ID"' "'"$PYTHON_BIN"'" -u -m jdcnet_exp.train --config "$cfg" > "$log_f" 2>&1
    rc=$?
    if [ $rc -eq 0 ]; then
      printf "%s\tDONE gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
    else
      printf "%s\tFAIL rc=%d gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$rc" "$name" | tee -a "'"$STATUS"'"
    fi
  ' _ {}
  log "PHASE_DONE: $phase_label"
done

log "H800_5FOLD_CV_COMPLETE tag=$TAG"
