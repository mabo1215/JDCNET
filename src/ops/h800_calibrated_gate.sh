#!/usr/bin/env bash
set -euo pipefail
# H800: A2 (calibrate-then-gate) + A3 (over-confidence ablation)
#
# Sweeps teacher CALIBRATION TEMPERATURE on the two gate-passing JDCNet cells:
#   T=1.0  raw confidence            (paper baseline)
#   T=0.5  over-confident teacher    (A3 stress test)
#   T=2.0  softened / better-calibrated (A2 calibrate-then-gate proxy)
#
# Cells:
#   3slice soft-KL  tau=0.70 lambda=1.0
#   mid    hard     tau=0.80 lambda=1.5
#
# 2 cells x 3 temperatures x 5 folds x 3 seeds = 90 runs.
#
# PREREQUISITE: run h800_bimcv_5fold_cv.sh first (or at least the teacher + supervised phases).
# Required on disk:
#   - Teacher checkpoints at $SUP_RUN_ROOT/{variant}_f{fold}_s{seed}_teacher/best.pt
#   - CV fold manifests at $CV_DIR/fold_XX/{prefix}_foldXX_paired_manifest.csv
#   - CT variant images at $CT_VARIANT_ROOT/bimcv_ct_{mid,3slice}/bimcv_S*.png
#
# Usage:
#   # Dry run — generate configs only:
#   DRY_RUN=true bash h800_calibrated_gate.sh
#
#   # Full run (GPU required):
#   bash h800_calibrated_gate.sh

# ---------- paths ----------
ROOT=${ROOT:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}

TAG=${TAG:-bimcv_h800_calibrated_gate}
SOURCE_TAG=${SOURCE_TAG:-bimcv_h800_5fold_cv}
CV_DIR=${CV_DIR:-/root/autodl-tmp/bimcv_cv/${SOURCE_TAG}}
PREFIX=${PREFIX:-bimcv_full_paired}
SUP_RUN_ROOT=${SUP_RUN_ROOT:-/root/autodl-tmp/runs/${SOURCE_TAG}}
RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-${ROOT}/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/${TAG}}
MANIFEST_DIR=${MANIFEST_DIR:-/root/autodl-tmp/bimcv_cv/${TAG}/manifests}

CT_VARIANT_ROOT=${CT_VARIANT_ROOT:-/root/autodl-tmp/data/bimcv_ct_variants}

# ---------- experiment grid ----------
CELLS=${CELLS:-"3slice:true:0.70:1.0 mid:false:0.80:1.5"}
TEMPS=${TEMPS:-"1.0 0.5 2.0"}
FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}

GPU_ID=${GPU_ID:-0}
MAX_PARALLEL=${MAX_PARALLEL:-8}
BATCH_SIZE=${BATCH_SIZE:-128}
NUM_WORKERS=${NUM_WORKERS:-8}
EPOCHS=${EPOCHS:-50}
INPUT_SIZE=${INPUT_SIZE:-224}
AMP=${AMP:-true}
LEARNING_RATE=${LEARNING_RATE:-3e-4}
MODEL_BACKBONE=${MODEL_BACKBONE:-resnet18}
DRY_RUN=${DRY_RUN:-false}

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR" "$MANIFEST_DIR"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
done_run(){ [ -s "$1/best.pt" ]; }

log "CALIB_GATE_START tag=$TAG cells=[$CELLS] temps=[$TEMPS] folds=[$FOLDS] seeds=[$SEEDS]"
cd "$ROOT"

# ---------- prerequisite check ----------
log "CHECKING PREREQUISITES"
"$PYTHON_BIN" - "$SUP_RUN_ROOT" "$CV_DIR" "$PREFIX" "$CT_VARIANT_ROOT" "$CELLS" "$FOLDS" "$SEEDS" <<'PY'
import sys, os, re
from pathlib import Path
sup, cv, prefix, ct_root = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
cells_raw, folds_raw, seeds_raw = sys.argv[5], sys.argv[6], sys.argv[7]
cells = [c.split(':') for c in cells_raw.split()]
folds = [int(x) for x in folds_raw.split()]
seeds = [int(x) for x in seeds_raw.split()]
variants = sorted({c[0] for c in cells})
issues = []
for v in variants:
    for fold in folds:
        m = cv / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_paired_manifest.csv'
        if not m.exists(): issues.append(f'Missing manifest: {m}')
        for seed in seeds:
            ckpt = sup / f'{v}_f{fold:02d}_s{seed}_teacher' / 'best.pt'
            if not ckpt.exists(): issues.append(f'Missing teacher: {ckpt}')
    vdir = ct_root / f'bimcv_ct_{v}'
    if vdir.exists():
        n = len(list(vdir.glob('bimcv_S*.png')))
        print(f'  CT variant {v}: {n} images')
    else:
        issues.append(f'Missing CT dir: {vdir}')
if issues:
    print(f'\nPREREQUISITE ISSUES ({len(issues)}):')
    for i in issues[:20]: print(f'  {i}')
    if len(issues) > 20: print(f'  ... and {len(issues)-20} more')
    print('\nRun h800_bimcv_5fold_cv.sh first to produce these prerequisites.')
    raise SystemExit(1)
print('\nAll prerequisites OK')
PY
log "PREREQUISITES_OK"

# ---------- generate configs ----------
export ROOT TAG CV_DIR PREFIX SUP_RUN_ROOT RUN_ROOT CONFIG_DIR LOG_DIR MANIFEST_DIR CT_VARIANT_ROOT \
  CELLS TEMPS FOLDS SEEDS BATCH_SIZE NUM_WORKERS EPOCHS INPUT_SIZE AMP LEARNING_RATE MODEL_BACKBONE

"$PYTHON_BIN" - <<'PY'
import json, os, re
from pathlib import Path
import pandas as pd

cv_dir = Path(os.environ['CV_DIR']); prefix = os.environ['PREFIX']
sup_run_root = Path(os.environ['SUP_RUN_ROOT'])
run_root = Path(os.environ['RUN_ROOT']); cfg_dir = Path(os.environ['CONFIG_DIR'])
man_dir = Path(os.environ['MANIFEST_DIR']); ct_root = Path(os.environ['CT_VARIANT_ROOT'])
cells = [c.split(':') for c in os.environ['CELLS'].split()]
temps = [float(x) for x in os.environ['TEMPS'].split()]
folds = [int(x) for x in os.environ['FOLDS'].split()]
seeds = [int(x) for x in os.environ['SEEDS'].split()]
batch = int(os.environ['BATCH_SIZE']); workers = int(os.environ['NUM_WORKERS'])
epochs = int(os.environ['EPOCHS']); input_size = int(os.environ['INPUT_SIZE'])
amp = os.environ['AMP'].lower() == 'true'; lr = float(os.environ['LEARNING_RATE'])
model_backbone = os.environ.get('MODEL_BACKBONE', 'resnet18')

variant_dirs = {
    'mid': ct_root / 'bimcv_ct_mid',
    '3slice': ct_root / 'bimcv_ct_3slice',
    'proj': ct_root / 'bimcv_ct_proj',
}
for p in [cfg_dir, man_dir]: p.mkdir(parents=True, exist_ok=True)


def patient_from_path(s):
    m = re.search(r'S\d+', str(s)); return m.group(0) if m else None


teachers_used = sorted({c[0] for c in cells})
common = None
for t in teachers_used:
    avail = {patient_from_path(x.name) for x in variant_dirs[t].glob('bimcv_S*.png')}
    avail.discard(None)
    common = avail if common is None else common & avail
common = set(common or [])


def teacher_ckpt(variant, fold, seed):
    return str(sup_run_root / f'{variant}_f{fold:02d}_s{seed}_teacher' / 'best.pt')


def temp_tag(T):
    return f"T{int(round(T*100)):03d}"


base_model = {
    'name': 'student', 'num_classes': 2, 'input_size': input_size,
    'use_dpe': False, 'use_mhra': False, 'use_dfpn': False,
    'paired_input': True, 'backbone': model_backbone,
}


def write_cfg(name, manifest_csv, variant, fold, seed, soft, tau, lam, T):
    cfg = {
        'experiment_name': name,
        'manifest_path': str(manifest_csv),
        'output_dir': str(run_root / name),
        'seed': int(seed),
        'model': base_model,
        'data': {
            'train_split': 'train', 'val_split': 'val',
            'train_modalities': ['xray'], 'val_modalities': ['xray'],
            'batch_size': batch, 'num_workers': workers,
            'paired_image_column': 'teacher_image_path',
            'use_weighted_sampler': True, 'pin_memory': True,
            'persistent_workers': workers > 0, 'prefetch_factor': 4 if workers > 0 else 2,
        },
        'optimization': {
            'epochs': epochs, 'learning_rate': lr, 'weight_decay': 1e-4,
            'grad_accum_steps': 1, 'amp': amp, 'channels_last': False,
            'torch_compile': False, 'validation_interval': 1,
        },
        'distillation': {'enabled': False},
        'pseudo_label': {
            'enabled': True,
            'teacher_checkpoint': teacher_ckpt(variant, fold, seed),
            'tau_pseudo': float(tau),
            'lambda_pseudo': float(lam),
            'soft': bool(soft),
            'soft_temperature': 1.0,
            'teacher_temperature': float(T),
        },
    }
    (cfg_dir / f'{name}.json').write_text(json.dumps(cfg, indent=2))


manifest_cache = {}
def student_manifest(t, fold):
    key = (t, fold)
    if key in manifest_cache: return manifest_cache[key]
    src = cv_dir / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_paired_manifest.csv'
    df = pd.read_csv(src)
    keep, vpaths = [], []
    for _, row in df.iterrows():
        pid = str(row['patient_id']).replace('bimcv_', '')
        ok = pid in common
        keep.append(ok)
        vpaths.append(str(variant_dirs[t] / f'bimcv_{pid}.png') if ok else '')
    dfs = df[keep].copy().reset_index(drop=True)
    dfs['teacher_image_path'] = [p for p, k in zip(vpaths, keep) if k]
    out = man_dir / f'{t}_fold{fold:02d}_student_manifest.csv'
    dfs.to_csv(out, index=False)
    manifest_cache[key] = out
    return out


names = []
for variant, soft_s, tau_s, lam_s in cells:
    soft = soft_s.lower() == 'true'
    tau = float(tau_s); lam = float(lam_s)
    tgt = 'soft' if soft else 'hard'
    for fold in folds:
        mcsv = student_manifest(variant, fold)
        for T in temps:
            for seed in seeds:
                name = f'{variant}_{tgt}_f{fold:02d}_s{seed}_{temp_tag(T)}'
                write_cfg(name, mcsv, variant, fold, seed, soft, tau, lam, T)
                names.append(name)

(Path(os.environ['LOG_DIR']) / 'cell_names.txt').write_text('\n'.join(names) + '\n')
print('calibrated-gate configs', len(names), 'common_patients', len(common))
PY

log "CONFIGS_GENERATED $(wc -l < "$LOG_DIR/cell_names.txt")"

if [ "$DRY_RUN" = "true" ]; then
  log "DRY_RUN configs only; not launching training"
  exit 0
fi

# ---------- launch training ----------
log "LAUNCHING TRAINING max_parallel=$MAX_PARALLEL gpu=$GPU_ID"

mapfile -t names < "$LOG_DIR/cell_names.txt"
printf '%s\n' "${names[@]}" | xargs -P "$MAX_PARALLEL" -I{} bash -c '
  name="$1"; cfg="'"$CONFIG_DIR"'/${name}.json"; run_dir="'"$RUN_ROOT"'/$name"
  log_f="'"$LOG_DIR"'/${name}.log"; test_cfg="'"$CONFIG_DIR"'/${name}.test.json"

  # Wait for teacher checkpoint if needed
  ckpt=$(python3 - "$cfg" <<PYX
import json, sys
print((json.load(open(sys.argv[1])).get("pseudo_label") or {}).get("teacher_checkpoint",""))
PYX
)
  if [ -n "$ckpt" ]; then for i in $(seq 1 720); do [ -s "$ckpt" ] && break; sleep 5; done; fi

  if [ -s "$run_dir/best.pt" ]; then
    printf "%s\tSKIP_DONE gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
  else
    printf "%s\tSTART gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
    CUDA_VISIBLE_DEVICES='"$GPU_ID"' "'"$PYTHON_BIN"'" -u -m jdcnet_exp.train_pseudolabel --config "$cfg" > "$log_f" 2>&1
    rc=$?
    if [ $rc -eq 0 ]; then
      printf "%s\tDONE gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
    else
      printf "%s\tFAIL rc=%d gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$rc" "$name" | tee -a "'"$STATUS"'"
      exit $rc
    fi
  fi

  # Test-split evaluation
  python3 - "$cfg" "$test_cfg" <<PYX
import json, sys
p = json.load(open(sys.argv[1])); p["data"] = dict(p["data"]); p["data"]["val_split"] = "test"
json.dump(p, open(sys.argv[2], "w"), indent=2)
PYX
  if [ -s "$run_dir/test_eval/metrics.json" ]; then
    printf "%s\tSKIP_TEST gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
  else
    CUDA_VISIBLE_DEVICES='"$GPU_ID"' "'"$PYTHON_BIN"'" -m jdcnet_exp.evaluate --config "$test_cfg" --checkpoint "$run_dir/best.pt" --output-dir "$run_dir/test_eval" >> "$log_f" 2>&1 \
      && printf "%s\tDONE_TEST gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'" \
      || printf "%s\tFAIL_TEST gpu='"$GPU_ID"' %s\n" "$(date -Is)" "$name" | tee -a "'"$STATUS"'"
  fi
' _ {}

log "CALIB_GATE_ALL_DONE tag=$TAG total=${#names[@]}"
