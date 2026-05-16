#!/usr/bin/env bash
set -euo pipefail
# Method 1: Cross-modal contrastive alignment (InfoNCE).
# Two-stage per cell: Stage 1 InfoNCE pretrain (X-ray + CT), Stage 2 supervised fine-tune.
# Reuses Stage A's BIMCV 510-patient paired manifests at /data1/midrc/bimcv_full_paired_cv_20260516.
# Sweep: 2 teachers (mid, 3slice) x 2 temperatures (0.07, 0.20) x 5 folds x 3 seeds = 60 contrastive runs.
# Supervised baseline runs reuse the Stage A outputs at /data1/midrc/runs/bimcv_full_paired_cv_20260516.

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
TAG=${TAG:-bimcv_contrastive_cv_20260516}
SOURCE_TAG=${SOURCE_TAG:-bimcv_full_paired_cv_20260516}
CV_DIR=${CV_DIR:-/data1/midrc/${SOURCE_TAG}}
PREFIX=${PREFIX:-bimcv_full_paired}
SUP_RUN_ROOT=${SUP_RUN_ROOT:-/data1/midrc/runs/${SOURCE_TAG}}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
MANIFEST_DIR=${MANIFEST_DIR:-/data1/midrc/${TAG}/manifests}
TEACHERS=${TEACHERS:-"mid 3slice"}
TEMPERATURES=${TEMPERATURES:-"0.07 0.20"}
FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
GPUS=${GPUS:-"0 1 2 3"}
CONCURRENCY=${CONCURRENCY:-4}
PRETRAIN_BATCH=${PRETRAIN_BATCH:-128}
FINETUNE_BATCH=${FINETUNE_BATCH:-128}
NUM_WORKERS=${NUM_WORKERS:-8}
PRETRAIN_EPOCHS=${PRETRAIN_EPOCHS:-100}
FINETUNE_EPOCHS=${FINETUNE_EPOCHS:-50}
INPUT_SIZE=${INPUT_SIZE:-224}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-false}
TORCH_COMPILE=${TORCH_COMPILE:-false}
PRETRAIN_LR=${PRETRAIN_LR:-1e-4}
FINETUNE_LR=${FINETUNE_LR:-3e-4}
PROJ_DIM=${PROJ_DIM:-128}

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR" "$MANIFEST_DIR"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }

log "CONTRASTIVE_START tag=$TAG teachers=[$TEACHERS] temps=[$TEMPERATURES] folds=[$FOLDS] seeds=[$SEEDS]"
cd "$ROOT"

export ROOT TAG CV_DIR PREFIX SUP_RUN_ROOT RUN_ROOT CONFIG_DIR LOG_DIR MANIFEST_DIR TEACHERS TEMPERATURES FOLDS SEEDS PRETRAIN_BATCH FINETUNE_BATCH NUM_WORKERS PRETRAIN_EPOCHS FINETUNE_EPOCHS INPUT_SIZE AMP CHANNELS_LAST TORCH_COMPILE PRETRAIN_LR FINETUNE_LR PROJ_DIM
"$PYTHON_BIN" - <<'PY'
import json, os, re
from pathlib import Path
import pandas as pd

cv_dir = Path(os.environ['CV_DIR']); prefix = os.environ['PREFIX']
run_root = Path(os.environ['RUN_ROOT']); cfg_dir = Path(os.environ['CONFIG_DIR'])
man_dir = Path(os.environ['MANIFEST_DIR']); log_dir = Path(os.environ['LOG_DIR'])
teachers = os.environ['TEACHERS'].split()
temperatures = [float(x) for x in os.environ['TEMPERATURES'].split()]
folds = [int(x) for x in os.environ['FOLDS'].split()]
seeds = [int(x) for x in os.environ['SEEDS'].split()]
pre_batch = int(os.environ['PRETRAIN_BATCH']); ft_batch = int(os.environ['FINETUNE_BATCH'])
workers = int(os.environ['NUM_WORKERS'])
pre_epochs = int(os.environ['PRETRAIN_EPOCHS']); ft_epochs = int(os.environ['FINETUNE_EPOCHS'])
input_size = int(os.environ['INPUT_SIZE'])
amp = os.environ['AMP'].lower() == 'true'
channels_last = os.environ['CHANNELS_LAST'].lower() == 'true'
torch_compile = os.environ['TORCH_COMPILE'].lower() == 'true'
pre_lr = float(os.environ['PRETRAIN_LR']); ft_lr = float(os.environ['FINETUNE_LR'])
proj_dim = int(os.environ['PROJ_DIM'])

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

base_model = {
    'name': 'student', 'num_classes': 2, 'input_size': input_size,
    'use_dpe': False, 'use_mhra': False, 'use_dfpn': False,
    'paired_input': False, 'backbone': 'resnet18',
}


def write_cfg(name, manifest_csv, teacher_kind, seed, temperature):
    cfg = {
        'experiment_name': name,
        'manifest_path': str(manifest_csv),
        'output_dir': str(run_root / name),
        'seed': int(seed),
        'model': base_model,
        'data': {
            'train_split': 'train', 'val_split': 'val',
            'train_modalities': ['xray'], 'val_modalities': ['xray'],
            'batch_size': ft_batch, 'num_workers': workers,
            'paired_image_column': 'teacher_image_path',
            'use_weighted_sampler': True, 'pin_memory': True,
            'persistent_workers': workers > 0, 'prefetch_factor': 4 if workers > 0 else 2,
        },
        'optimization': {
            'epochs': ft_epochs, 'learning_rate': ft_lr, 'weight_decay': 1e-4,
            'grad_accum_steps': 1, 'amp': amp, 'channels_last': channels_last,
            'torch_compile': torch_compile, 'validation_interval': 1,
        },
        'distillation': {'enabled': False},
        'contrastive': {
            'enabled': True,
            'embedding_dim': proj_dim,
            'projection_hidden_dim': proj_dim,
            'pretrain_epochs': pre_epochs,
            'pretrain_lr': pre_lr,
            'pretrain_weight_decay': 1e-4,
            'pretrain_batch_size': pre_batch,
            'temperature': float(temperature),
            'teacher_image_column': 'teacher_image_path',
            'finetune_epochs': ft_epochs,
            'finetune_lr': ft_lr,
            'freeze_ct_encoder': False,
            'init_from_imagenet': True,
        },
    }
    (cfg_dir / f'{name}.json').write_text(json.dumps(cfg, indent=2))


names = []
for t in teachers:
    for fold in folds:
        src = cv_dir / f'fold_{fold:02d}' / f'{prefix}_fold{fold:02d}_paired_manifest.csv'
        df = pd.read_csv(src)
        keep = []
        vpaths = []
        for _, row in df.iterrows():
            pid = str(row['patient_id']).replace('bimcv_', '')
            ok = pid in common
            keep.append(ok)
            vpaths.append(variant_path(t, pid) if ok else '')
        dfs = df[keep].copy().reset_index(drop=True)
        vpaths = [p for p, k in zip(vpaths, keep) if k]
        dfs['teacher_image_path'] = vpaths
        student_csv = man_dir / f'{t}_fold{fold:02d}_student_manifest.csv'
        dfs.to_csv(student_csv, index=False)
        print(f'{t} fold{fold}: rows={len(dfs)} pos={(dfs.label==1).sum()} neg={(dfs.label==0).sum()}')
        for tau in temperatures:
            tau_tag = f"t{int(round(tau*100)):03d}"  # 0.07 -> t007, 0.20 -> t020
            for seed in seeds:
                name = f'{t}_f{fold:02d}_s{seed}_contrastive_{tau_tag}'
                write_cfg(name, student_csv, t, seed, tau)
                names.append(name)

(log_dir / 'cell_names.txt').write_text('\n'.join(names) + '\n')
print('contrastive configs', len(names), 'common_patients', len(common))
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
  if done_run "\$run_dir"; then
    log "SKIP_DONE gpu=\$gpu \$name"
  else
    log "START gpu=\$gpu \$name"
    CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -u -m jdcnet_exp.train_contrastive --config "\$cfg" > "\$log_f" 2>&1
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
  screen -S "contrastive_g${gpu}" -X quit >/dev/null 2>&1 || true
  screen -dmS "contrastive_g${gpu}" bash "$LOG_DIR/gpu${gpu}_queue.sh"
  log "LAUNCHED gpu=$gpu runs=${#assigned[@]}"
done
log "CONTRASTIVE_ALL_LAUNCHED total=${#names[@]}"
screen -ls | grep contrastive || true
