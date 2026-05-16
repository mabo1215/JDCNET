#!/usr/bin/env bash
set -euo pipefail
# Method 2: CT pseudo-label semi-supervised training on the 510-patient BIMCV paired cohort.
# Reuses Stage A teacher checkpoints at /data1/midrc/runs/bimcv_full_paired_cv_20260516/{variant}_f{fold}_s{seed}_teacher/best.pt
# Reuses Stage A paired manifests (with the same teacher_image_path column) so the supervised baseline at
# /data1/midrc/runs/bimcv_full_paired_cv_20260516/{variant}_f{fold}_s{seed}_supervised/ is a valid same-split comparator.
# Sweep: 2 teachers (mid, 3slice) x 2 tau_pseudo (0.70, 0.80) x 2 lambda (0.5, 1.0) x 5 folds x 3 seeds = 120 runs.

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
TAG=${TAG:-bimcv_pseudolabel_cv_20260516}
SOURCE_TAG=${SOURCE_TAG:-bimcv_full_paired_cv_20260516}
CV_DIR=${CV_DIR:-/data1/midrc/${SOURCE_TAG}}
PREFIX=${PREFIX:-bimcv_full_paired}
SUP_RUN_ROOT=${SUP_RUN_ROOT:-/data1/midrc/runs/${SOURCE_TAG}}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
MANIFEST_DIR=${MANIFEST_DIR:-/data1/midrc/${TAG}/manifests}
TEACHERS=${TEACHERS:-"mid 3slice"}
TAUS=${TAUS:-"0.70 0.80"}
LAMBDAS=${LAMBDAS:-"0.5 1.0"}
FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
GPUS=${GPUS:-"2 3"}
CONCURRENCY=${CONCURRENCY:-4}
BATCH_SIZE=${BATCH_SIZE:-128}
NUM_WORKERS=${NUM_WORKERS:-8}
EPOCHS=${EPOCHS:-50}
INPUT_SIZE=${INPUT_SIZE:-224}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-false}
LEARNING_RATE=${LEARNING_RATE:-3e-4}
SOFT=${SOFT:-false}

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR" "$MANIFEST_DIR"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }

log "PSEUDOLABEL_START tag=$TAG teachers=[$TEACHERS] taus=[$TAUS] lambdas=[$LAMBDAS] folds=[$FOLDS] seeds=[$SEEDS] soft=$SOFT"
cd "$ROOT"

export ROOT TAG CV_DIR PREFIX SUP_RUN_ROOT RUN_ROOT CONFIG_DIR LOG_DIR MANIFEST_DIR TEACHERS TAUS LAMBDAS FOLDS SEEDS BATCH_SIZE NUM_WORKERS EPOCHS INPUT_SIZE AMP CHANNELS_LAST LEARNING_RATE SOFT
"$PYTHON_BIN" - <<'PY'
import json, os, re
from pathlib import Path
import pandas as pd

cv_dir = Path(os.environ['CV_DIR']); prefix = os.environ['PREFIX']
sup_run_root = Path(os.environ['SUP_RUN_ROOT'])
run_root = Path(os.environ['RUN_ROOT']); cfg_dir = Path(os.environ['CONFIG_DIR'])
man_dir = Path(os.environ['MANIFEST_DIR']); log_dir = Path(os.environ['LOG_DIR'])
teachers = os.environ['TEACHERS'].split()
taus = [float(x) for x in os.environ['TAUS'].split()]
lambdas = [float(x) for x in os.environ['LAMBDAS'].split()]
folds = [int(x) for x in os.environ['FOLDS'].split()]
seeds = [int(x) for x in os.environ['SEEDS'].split()]
batch = int(os.environ['BATCH_SIZE']); workers = int(os.environ['NUM_WORKERS'])
epochs = int(os.environ['EPOCHS']); input_size = int(os.environ['INPUT_SIZE'])
amp = os.environ['AMP'].lower() == 'true'
channels_last = os.environ['CHANNELS_LAST'].lower() == 'true'
lr = float(os.environ['LEARNING_RATE'])
soft = os.environ['SOFT'].lower() == 'true'

variant_dirs = {
    'mid': Path('/dev/shm/bimcv_ct_mid'),
    '3slice': Path('/dev/shm/bimcv_ct_3slice'),
    'proj': Path('/dev/shm/bimcv_ct_proj'),
}
for p in [cfg_dir, man_dir]:
    p.mkdir(parents=True, exist_ok=True)


def patient_from_path(s):
    m = re.search(r'S\d+', str(s))
    return m.group(0) if m else None


def variant_path(t, pid):
    return str(variant_dirs[t] / f'bimcv_{pid}.png')


common = None
for t in teachers:
    avail = {patient_from_path(x.name) for x in variant_dirs[t].glob('bimcv_S*.png')}
    avail.discard(None)
    common = avail if common is None else common & avail
common = set(common or [])


def tau_tag(tau):
    return f"t{int(round(tau*100)):03d}"


def lam_tag(lam):
    return f"l{int(round(lam*100)):03d}"


base_model = {
    'name': 'student', 'num_classes': 2, 'input_size': input_size,
    'use_dpe': False, 'use_mhra': False, 'use_dfpn': False,
    'paired_input': True,  # enables paired data loader (teacher CT image accompanies xray)
    'backbone': 'resnet18',
}


def teacher_ckpt(variant, fold, seed):
    return str(sup_run_root / f'{variant}_f{fold:02d}_s{seed}_teacher' / 'best.pt')


def write_cfg(name, manifest_csv, variant, fold, seed, tau, lam):
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
            'grad_accum_steps': 1, 'amp': amp, 'channels_last': channels_last,
            'torch_compile': False, 'validation_interval': 1,
        },
        'distillation': {'enabled': False},
        'pseudo_label': {
            'enabled': True,
            'teacher_checkpoint': teacher_ckpt(variant, fold, seed),
            'tau_pseudo': float(tau),
            'lambda_pseudo': float(lam),
            'soft': soft,
            'soft_temperature': 1.0,
        },
    }
    (cfg_dir / f'{name}.json').write_text(json.dumps(cfg, indent=2))


names = []
for t in teachers:
    for fold in folds:
        src = cv_dir / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_paired_manifest.csv'
        df = pd.read_csv(src)
        keep_rows = []
        vpaths = []
        for _, row in df.iterrows():
            pid = str(row['patient_id']).replace('bimcv_', '')
            ok = pid in common
            keep_rows.append(ok)
            vpaths.append(variant_path(t, pid) if ok else '')
        dfs = df[keep_rows].copy().reset_index(drop=True)
        vpaths = [p for p, k in zip(vpaths, keep_rows) if k]
        dfs['teacher_image_path'] = vpaths
        student_csv = man_dir / f'{t}_fold{fold:02d}_student_manifest.csv'
        dfs.to_csv(student_csv, index=False)
        print(f'{t} fold{fold}: rows={len(dfs)} pos={(dfs.label==1).sum()} neg={(dfs.label==0).sum()}')
        for tau in taus:
            for lam in lambdas:
                for seed in seeds:
                    name = f'{t}_f{fold:02d}_s{seed}_pseudolabel_{tau_tag(tau)}_{lam_tag(lam)}'
                    write_cfg(name, student_csv, t, fold, seed, tau, lam)
                    names.append(name)

(log_dir / 'cell_names.txt').write_text('\n'.join(names) + '\n')
print('pseudolabel configs', len(names), 'common_patients', len(common))
PY

log "CONFIGS_GENERATED $(wc -l < "$LOG_DIR/cell_names.txt")"

write_queue() {
  local gpu="$1"; shift
  local script="$LOG_DIR/gpu${gpu}_queue.sh"
  local qfile="$LOG_DIR/gpu${gpu}_names.txt"
  printf '%s\n' "$@" > "$qfile"
  cat > "$script" <<EOF
#!/usr/bin/env bash
set -u
cd '$ROOT'
STATUS='$STATUS'; LOG_DIR='$LOG_DIR'; CONFIG_DIR='$CONFIG_DIR'; RUN_ROOT='$RUN_ROOT'; PYTHON_BIN='$PYTHON_BIN'; gpu='$gpu'
log(){ printf '%s\t%s\n' "\$(date -Is)" "\$*" | tee -a "\$STATUS"; }
done_run(){ [ -s "\$1/best.pt" ]; }
done_test(){ [ -s "\$1/test_eval/metrics.json" ]; }
run_one(){
  local name="\$1"
  local cfg="\$CONFIG_DIR/\${name}.json"
  local run_dir="\$RUN_ROOT/\$name"
  local log_f="\$LOG_DIR/\${name}.log"
  local test_cfg="\$CONFIG_DIR/\${name}.test.json"
  local ckpt
  ckpt=\$(python3 - "\$cfg" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
print((p.get('pseudo_label') or {}).get('teacher_checkpoint', ''))
PY
)
  if [ -n "\$ckpt" ]; then for i in \$(seq 1 720); do [ -s "\$ckpt" ] && break; sleep 5; done; fi
  if done_run "\$run_dir"; then
    log "SKIP_DONE gpu=\$gpu \$name"
  else
    log "START gpu=\$gpu \$name"
    CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -u -m jdcnet_exp.train_pseudolabel --config "\$cfg" > "\$log_f" 2>&1
    rc=\$?
    if [ \$rc -eq 0 ]; then log "DONE gpu=\$gpu \$name"; else log "FAIL rc=\$rc gpu=\$gpu \$name"; return \$rc; fi
  fi
  "\$PYTHON_BIN" - "\$cfg" "\$test_cfg" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
p['data'] = dict(p['data']); p['data']['val_split'] = 'test'
json.dump(p, open(sys.argv[2], 'w'), indent=2)
PY
  if done_test "\$run_dir"; then
    log "SKIP_TEST gpu=\$gpu \$name"
  else
    CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -m jdcnet_exp.evaluate --config "\$test_cfg" --checkpoint "\$run_dir/best.pt" --output-dir "\$run_dir/test_eval" >> "\$log_f" 2>&1 \
      && log "DONE_TEST gpu=\$gpu \$name" \
      || log "FAIL_TEST gpu=\$gpu \$name"
  fi
}
export -f run_one log done_run done_test
export STATUS LOG_DIR CONFIG_DIR RUN_ROOT PYTHON_BIN gpu
cat '$qfile' | xargs -I{} -P '$CONCURRENCY' bash -c 'run_one "\$@"' _ {}
log "GPU_QUEUE_DONE gpu=\$gpu"
EOF
  chmod +x "$script"
}

mapfile -t gpus < <(printf '%s\n' $GPUS)
mapfile -t names < "$LOG_DIR/cell_names.txt"
for gi in "${!gpus[@]}"; do
  gpu="${gpus[$gi]}"
  assigned=()
  for idx in "${!names[@]}"; do
    if [ $((idx % ${#gpus[@]})) -eq "$gi" ]; then assigned+=("${names[$idx]}"); fi
  done
  write_queue "$gpu" "${assigned[@]}"
  screen -S "pseudolabel_g${gpu}" -X quit >/dev/null 2>&1 || true
  screen -dmS "pseudolabel_g${gpu}" bash "$LOG_DIR/gpu${gpu}_queue.sh"
  log "LAUNCHED gpu=$gpu runs=${#assigned[@]}"
done
log "PSEUDOLABEL_ALL_LAUNCHED total=${#names[@]}"
screen -ls | grep pseudolabel || true
