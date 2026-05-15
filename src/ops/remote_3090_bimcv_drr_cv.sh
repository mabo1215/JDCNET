#!/usr/bin/env bash
set -euo pipefail
# BIMCV DRR Teacher + Extended Seeds + Batch Sensitivity experiments
# Plan: docs/tmp/report516.md
# Exp1: DRR teacher 5-fold (60 runs, seeds 42-44)
# Exp2: Extended seeds 45-47 for CT mid-slice gated KD (45 runs)
# Exp3: batch=64 sensitivity (15 runs, reuse existing teacher ckpts)
# GPU strategy: 4x RTX3090, 3 concurrent per GPU = 12 simultaneous

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
CV_DIR=${CV_DIR:-/data1/midrc/bimcv_only_cv_20260514}
PREFIX=${PREFIX:-bimcv_only}
BASE_RUN_ROOT=${BASE_RUN_ROOT:-/data1/midrc/runs/bimcv_only_5fold_cv_balanced}

TAG=${TAG:-bimcv_drr_cv_20260515}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
DRR_SHM=${DRR_SHM:-/dev/shm/bimcv_drr}
DRR_SRC=${DRR_SRC:-/data/bimcv/drr_cache}
DRR_MANIFEST_DIR=${DRR_MANIFEST_DIR:-/data1/midrc/bimcv_drr_cv_20260515}

FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS_E1=${SEEDS_E1:-"42 43 44"}
SEEDS_E2=${SEEDS_E2:-"45 46 47"}
SEEDS_E3=${SEEDS_E3:-"42 43 44"}

GPUS=${GPUS:-"0 1 2 3"}
CONCURRENCY=${CONCURRENCY:-3}
EPOCHS=${EPOCHS:-50}
INPUT_SIZE=${INPUT_SIZE:-224}
BATCH_SIZE=${BATCH_SIZE:-256}
BATCH_SIZE_E3=${BATCH_SIZE_E3:-64}
NUM_WORKERS=${NUM_WORKERS:-1}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-false}
VALIDATION_INTERVAL=${VALIDATION_INTERVAL:-1}
USE_WEIGHTED_SAMPLER=${USE_WEIGHTED_SAMPLER:-true}
ALPHA=${ALPHA:-0.6}
GATE_FLOOR=${GATE_FLOOR:-0.0}
T_DRR=${T_DRR:-4.0}
THR_DRR=${THR_DRR:-0.50}
T_E2=${T_E2:-4.0}
THR_E2=${THR_E2:-0.50}

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR" "$DRR_MANIFEST_DIR" "$DRR_SHM"

STATUS="$LOG_DIR/status.tsv"
touch "$STATUS"

log() { printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
done_run() { [ -s "$1/best_metrics.json" ] && [ -s "$1/best.pt" ]; }
done_test_eval() { [ -s "$1/test_eval/metrics.json" ]; }

log "EXPERIMENT_START tag=$TAG gpus=[$GPUS] concurrency=$CONCURRENCY"

# ── Step 1: Copy DRR images to /dev/shm ──────────────────────────────────────
log "COPY_DRR_START src=$DRR_SRC -> $DRR_SHM"
cp "$DRR_SRC"/bimcv_S*.png "$DRR_SHM"/
DRR_COUNT=$(ls "$DRR_SHM"/*.png | wc -l)
log "COPY_DRR_DONE count=$DRR_COUNT"

# ── Step 2: Generate DRR manifests + all configs ──────────────────────────────
export ROOT RUN_ROOT BASE_RUN_ROOT CONFIG_DIR CV_DIR LOG_DIR DRR_SHM DRR_MANIFEST_DIR PREFIX
export FOLDS SEEDS_E1 SEEDS_E2 SEEDS_E3
export EPOCHS INPUT_SIZE BATCH_SIZE BATCH_SIZE_E3 NUM_WORKERS AMP CHANNELS_LAST
export TORCH_COMPILE VALIDATION_INTERVAL USE_WEIGHTED_SAMPLER ALPHA GATE_FLOOR
export T_DRR THR_DRR T_E2 THR_E2 TAG

"$PYTHON_BIN" - << 'PY'
import json, os, re, shutil
import pandas as pd
from pathlib import Path

cv_dir = Path(os.environ["CV_DIR"])
prefix = os.environ["PREFIX"]
drr_shm = Path(os.environ["DRR_SHM"])
drr_manifest_dir = Path(os.environ["DRR_MANIFEST_DIR"])
run_root = Path(os.environ["RUN_ROOT"])
base_run_root = Path(os.environ["BASE_RUN_ROOT"])
config_dir = Path(os.environ["CONFIG_DIR"])
log_dir = Path(os.environ["LOG_DIR"])
tag = os.environ["TAG"]

folds = [int(x) for x in os.environ["FOLDS"].split()]
seeds_e1 = [int(x) for x in os.environ["SEEDS_E1"].split()]
seeds_e2 = [int(x) for x in os.environ["SEEDS_E2"].split()]
seeds_e3 = [int(x) for x in os.environ["SEEDS_E3"].split()]

epochs = int(os.environ["EPOCHS"])
input_size = int(os.environ["INPUT_SIZE"])
batch_size = int(os.environ["BATCH_SIZE"])
batch_size_e3 = int(os.environ["BATCH_SIZE_E3"])
num_workers = int(os.environ["NUM_WORKERS"])
amp = os.environ["AMP"].lower() == "true"
channels_last = os.environ["CHANNELS_LAST"].lower() == "true"
torch_compile = os.environ["TORCH_COMPILE"].lower() == "true"
val_interval = int(os.environ["VALIDATION_INTERVAL"])
weighted = os.environ["USE_WEIGHTED_SAMPLER"].lower() == "true"
alpha = float(os.environ["ALPHA"])
gate_floor = float(os.environ["GATE_FLOOR"])
t_drr = float(os.environ["T_DRR"])
thr_drr = float(os.environ["THR_DRR"])
t_e2 = float(os.environ["T_E2"])
thr_e2 = float(os.environ["THR_E2"])

# DRR patients available
drr_patients = set(
    re.search(r'bimcv_(S\d+)', f).group(1)
    for f in os.listdir(str(drr_shm)) if f.endswith('.png')
)

def get_patient_id(path_str):
    m = re.search(r'sub-(S\d+)', str(path_str))
    return m.group(1) if m else None

# ── Generate DRR manifests (teacher + student) + CT teacher manifests ─────────
print("[setup] generating manifests...")
drr_teacher_manifest_paths = {}  # image_path = DRR path
drr_student_manifest_paths = {}  # image_path = X-ray, teacher_image_path = DRR
ct_teacher_manifest_paths = {}   # image_path = CT mid-slice path (for Exp2)

for fold in folds:
    src_csv = cv_dir / f"fold_{fold:02d}" / f"{prefix}_fold{fold:02d}_paired_manifest.csv"
    df = pd.read_csv(src_csv)

    # Extract patient ID for each row and build DRR paths
    drr_paths = []
    keep = []
    for _, row in df.iterrows():
        pid = get_patient_id(row['image_path'])
        if pid and pid in drr_patients:
            drr_paths.append(str(drr_shm / f"bimcv_{pid}.png"))
            keep.append(True)
        else:
            drr_paths.append(None)
            keep.append(False)

    df_s = df[keep].copy().reset_index(drop=True)
    drr_paths_filtered = [p for p, k in zip(drr_paths, keep) if k]

    # Student manifest: image_path = X-ray, teacher_image_path = DRR
    df_s['teacher_image_path'] = drr_paths_filtered
    student_csv = drr_manifest_dir / f"drr_fold{fold:02d}_student_manifest.csv"
    df_s.to_csv(str(student_csv), index=False)
    drr_student_manifest_paths[fold] = str(student_csv)

    # Teacher manifest: image_path = DRR (swap so data.py loads DRR images)
    df_t = df_s.copy()
    df_t['teacher_image_path'] = df_s['image_path']
    df_t['image_path'] = drr_paths_filtered
    teacher_csv = drr_manifest_dir / f"drr_fold{fold:02d}_teacher_manifest.csv"
    df_t.to_csv(str(teacher_csv), index=False)
    drr_teacher_manifest_paths[fold] = str(teacher_csv)

    # CT teacher manifest (Exp2): image_path = CT mid-slice (from teacher_image_path column)
    df_ct_t = df.copy()
    df_ct_t['teacher_image_path'] = df['image_path']
    df_ct_t['image_path'] = df['teacher_image_path']
    ct_teacher_csv = drr_manifest_dir / f"ct_fold{fold:02d}_teacher_manifest.csv"
    df_ct_t.to_csv(str(ct_teacher_csv), index=False)
    ct_teacher_manifest_paths[fold] = str(ct_teacher_csv)

    n_pos = (df_s['label']==1).sum()
    n_neg = (df_s['label']==0).sum()
    print(f"  fold{fold}: student={len(df_s)} rows (pos={n_pos}, neg={n_neg}), "
          f"excluded={(~pd.Series(keep)).sum()}")

# ── Model / data / optim helpers ─────────────────────────────────────────────
base_model = {
    "name": "student", "num_classes": 2, "input_size": input_size,
    "use_dpe": False, "use_mhra": False, "use_dfpn": False, "paired_input": False,
    "backbone": "resnet18",
}

def data_cfg(modalities, batch, paired_col=None):
    d = {
        "train_split": "train", "val_split": "val",
        "train_modalities": modalities, "val_modalities": modalities,
        "batch_size": batch, "num_workers": num_workers,
        "use_weighted_sampler": weighted, "pin_memory": True,
        "persistent_workers": num_workers > 0,
        "prefetch_factor": 4 if num_workers > 0 else None,
    }
    if paired_col:
        d["paired_image_column"] = paired_col
    return d

def optim_cfg(ep=None):
    return {
        "epochs": ep or epochs,
        "learning_rate": 3e-4, "weight_decay": 1e-4,
        "grad_accum_steps": 1, "amp": amp, "channels_last": channels_last,
        "torch_compile": torch_compile, "validation_interval": val_interval,
    }

def gated_kd_dist(t, thr, teacher_ckpt):
    return {
        "enabled": True, "temperature": t, "alpha": alpha,
        "teacher_checkpoint": teacher_ckpt,
        "confidence_gate_enabled": True, "confidence_gate_threshold": thr,
        "confidence_gate_floor": gate_floor, "confidence_gate_power": 1.0,
        "confidence_gate_requires_correct": True,
        "confidence_gate_positive_threshold": -1.0,
        "confidence_gate_negative_threshold": -1.0,
        "confidence_gate_min_margin": 0.0, "confidence_gate_max_entropy": -1.0,
        "projected_attention_weight": 0.0,
    }

def plain_kd_dist(t, teacher_ckpt):
    return {
        "enabled": True, "temperature": t, "alpha": alpha,
        "teacher_checkpoint": teacher_ckpt,
        "confidence_gate_enabled": False, "projected_attention_weight": 0.0,
    }

all_names = []  # (name, priority) - lower priority runs first (teachers=0)

def write_cfg(name, manifest, model, data, optim, distill=None, priority=1):
    cfg = {
        "experiment_name": name,
        "manifest_path": manifest,
        "output_dir": str(run_root / name),
        "seed": int(re.search(r'_s(\d+)', name).group(1)),
        "model": model, "data": data, "optimization": optim,
        "distillation": distill or {"enabled": False},
    }
    (config_dir / f"{name}.json").write_text(json.dumps(cfg, indent=2))
    all_names.append((name, priority))

# ── EXP 1: DRR Teacher 5-fold (seeds 42-44) ──────────────────────────────────
print("[exp1] generating DRR teacher configs...")
for fold in folds:
    for seed in seeds_e1:
        tag_fs = f"e1_f{fold:02d}_s{seed}"
        teacher_ckpt = str(run_root / f"drr_{tag_fs}_teacher" / "best.pt")

        t_manifest = drr_teacher_manifest_paths[fold]  # image_path = DRR
        s_manifest = drr_student_manifest_paths[fold]  # image_path = X-ray

        # Row 1: DRR teacher (train_modalities=["xray"] since modality col = "xray")
        write_cfg(f"drr_{tag_fs}_teacher", t_manifest,
                  base_model, data_cfg(["xray"], batch_size), optim_cfg(),
                  priority=0)
        # Row 2: X-ray supervised
        write_cfg(f"drr_{tag_fs}_supervised", s_manifest,
                  base_model, data_cfg(["xray"], batch_size), optim_cfg(),
                  priority=1)
        # Row 3: Plain DRR logit KD
        write_cfg(f"drr_{tag_fs}_plain_kd", s_manifest,
                  base_model, data_cfg(["xray"], batch_size, "teacher_image_path"),
                  optim_cfg(), plain_kd_dist(t_drr, teacher_ckpt), priority=2)
        # Row 4: Gated DRR KD
        write_cfg(f"drr_{tag_fs}_gated_kd_t{int(t_drr*10):03d}_thr{int(thr_drr*100):03d}",
                  s_manifest,
                  base_model, data_cfg(["xray"], batch_size, "teacher_image_path"),
                  optim_cfg(), gated_kd_dist(t_drr, thr_drr, teacher_ckpt), priority=2)

# ── EXP 2: Extended seeds 45-47, CT mid-slice gated KD ───────────────────────
print("[exp2] generating extended-seeds configs (CT mid-slice, seeds 45-47)...")
for fold in folds:
    orig_manifest = str(cv_dir / f"fold_{fold:02d}" / f"{prefix}_fold{fold:02d}_paired_manifest.csv")
    ct_t_manifest = ct_teacher_manifest_paths[fold]  # image_path = CT mid-slice
    for seed in seeds_e2:
        name_fs = f"e2_f{fold:02d}_s{seed}"  # fixed: no double e2_ prefix
        teacher_ckpt = str(run_root / f"{name_fs}_teacher" / "best.pt")

        # Row 1: CT mid-slice teacher (train_modalities=["xray"] since modality col = "xray")
        write_cfg(f"{name_fs}_teacher", ct_t_manifest,
                  base_model, data_cfg(["xray"], batch_size), optim_cfg(),
                  priority=0)
        # Row 2: X-ray supervised (new seeds)
        write_cfg(f"{name_fs}_supervised", orig_manifest,
                  base_model, data_cfg(["xray"], batch_size), optim_cfg(),
                  priority=1)
        # Row 3: Gated KD T=4, thr=0.50 (new seeds)
        write_cfg(f"{name_fs}_gated_kd_t{int(t_e2*10):03d}_thr{int(thr_e2*100):03d}",
                  orig_manifest,
                  base_model, data_cfg(["xray"], batch_size, "teacher_image_path"),
                  optim_cfg(), gated_kd_dist(t_e2, thr_e2, teacher_ckpt), priority=2)

# ── EXP 3: Batch=64 sensitivity, gated KD, seeds 42-44 ───────────────────────
print("[exp3] generating batch=64 configs...")
for fold in folds:
    orig_manifest = str(cv_dir / f"fold_{fold:02d}" / f"{prefix}_fold{fold:02d}_paired_manifest.csv")
    for seed in seeds_e3:
        tag_fs = f"e3_f{fold:02d}_s{seed}"
        # Reuse existing teacher_drr checkpoints from original run
        teacher_ckpt = str(base_run_root / f"{prefix}_f{fold:02d}_s{seed}_teacher_drr" / "best.pt")
        if not Path(teacher_ckpt).exists():
            print(f"  WARNING missing teacher ckpt: {teacher_ckpt}")
        write_cfg(f"e3_{tag_fs}_gated_kd_b64_t{int(t_e2*10):03d}_thr{int(thr_e2*100):03d}",
                  orig_manifest,
                  base_model, data_cfg(["xray"], batch_size_e3, "teacher_image_path"),
                  optim_cfg(), gated_kd_dist(t_e2, thr_e2, teacher_ckpt), priority=3)

# Sort by priority then name so teachers run first
all_names.sort(key=lambda x: (x[1], x[0]))
names_ordered = [n for n, _ in all_names]

manifest_path = log_dir / "cell_names.txt"
manifest_path.write_text("\n".join(names_ordered) + "\n")
print(f"[done] wrote {len(names_ordered)} configs to {config_dir}")
print(f"  exp1 (DRR teacher): {sum(1 for n in names_ordered if n.startswith('drr_'))} runs")
print(f"  exp2 (ext seeds):   {sum(1 for n in names_ordered if n.startswith('e2_'))} runs")
print(f"  exp3 (batch64):     {sum(1 for n in names_ordered if n.startswith('e3_'))} runs")
PY

if [ ! -s "$LOG_DIR/cell_names.txt" ]; then
  log "FATAL no configs generated"; exit 1
fi

NUM_RUNS=$(wc -l < "$LOG_DIR/cell_names.txt")
log "GENERATED_RUNS=$NUM_RUNS configs=$CONFIG_DIR"

# ── Step 3: Concurrent launch (4 GPU × 3 workers) ────────────────────────────
eval_test() {
  local name="$1"
  local cfg="$CONFIG_DIR/${name}.json"
  local run_dir="$RUN_ROOT/${name}"
  local test_cfg="$CONFIG_DIR/${name}.test.json"
  "$PYTHON_BIN" - "$cfg" "$test_cfg" << 'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src))
p["data"] = dict(p["data"]); p["data"]["val_split"] = "test"
json.dump(p, open(dst,"w"), indent=2)
PY
  if done_test_eval "$run_dir"; then
    log "SKIP_TEST_EVAL $name"
  else
    CUDA_VISIBLE_DEVICES=$gpu "$PYTHON_BIN" -m jdcnet_exp.evaluate \
      --config "$test_cfg" --checkpoint "$run_dir/best.pt" \
      --output-dir "$run_dir/test_eval" \
      > "$LOG_DIR/${name}.test_eval.log" 2>&1
    log "DONE_TEST_EVAL $name"
  fi
}
export -f eval_test log done_run done_test_eval
export CONFIG_DIR RUN_ROOT LOG_DIR STATUS PYTHON_BIN ROOT

write_queue() {
  local gpu="$1"; shift
  local names=("$@")
  local script="$LOG_DIR/gpu${gpu}_queue.sh"
  {
    echo "#!/usr/bin/env bash"
    echo "set -euo pipefail"
    echo "cd '$ROOT'"
    echo "STATUS='$STATUS'"
    echo "LOG_DIR='$LOG_DIR'"
    echo "CONFIG_DIR='$CONFIG_DIR'"
    echo "RUN_ROOT='$RUN_ROOT'"
    echo "PYTHON_BIN='$PYTHON_BIN'"
    echo "gpu=$gpu"
    echo 'log(){ printf "%s\t%s\n" "$(date -Is)" "$*" | tee -a "$STATUS"; }'
    echo 'done_run(){ [ -s "$1/best_metrics.json" ] && [ -s "$1/best.pt" ]; }'
    echo 'done_test_eval(){ [ -s "$1/test_eval/metrics.json" ]; }'
    # Print run_one function
    cat << 'FUNC'
run_one(){
  local gpu=$1 name=$2
  local cfg="$CONFIG_DIR/${name}.json"
  local run_dir="$RUN_ROOT/${name}"
  local log_f="$LOG_DIR/${name}.log"
  local test_cfg="$CONFIG_DIR/${name}.test.json"
  if done_run "$run_dir"; then
    log "SKIP_DONE $name"
  else
    log "START gpu=$gpu $name"
    CUDA_VISIBLE_DEVICES=$gpu "$PYTHON_BIN" -u -m jdcnet_exp.train \
      --config "$cfg" > "$log_f" 2>&1
    log "DONE gpu=$gpu $name"
  fi
  # test_eval
  "$PYTHON_BIN" - "$cfg" "$test_cfg" << 'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src))
p["data"] = dict(p["data"]); p["data"]["val_split"] = "test"
json.dump(p, open(dst, "w"), indent=2)
PY
  if done_test_eval "$run_dir"; then
    log "SKIP_TEST_EVAL $name"
  else
    CUDA_VISIBLE_DEVICES=$gpu "$PYTHON_BIN" -m jdcnet_exp.evaluate \
      --config "$test_cfg" --checkpoint "$run_dir/best.pt" \
      --output-dir "$run_dir/test_eval" \
      >> "$log_f" 2>&1
    log "DONE_TEST_EVAL $name"
  fi
}
FUNC
    echo 'export -f run_one log done_run done_test_eval'
    echo "export CONFIG_DIR='$CONFIG_DIR' RUN_ROOT='$RUN_ROOT' LOG_DIR='$LOG_DIR' STATUS='$STATUS' PYTHON_BIN='$PYTHON_BIN'"

    # Write queue file for this GPU
    local qfile="$LOG_DIR/gpu${gpu}_names.txt"
    printf '%s\n' "${names[@]}" > "$qfile"
    echo "cat '$qfile' | xargs -I{} -P $CONCURRENCY bash -c 'run_one $gpu \"\$@\"' _ {}"
    echo "log 'GPU_QUEUE_DONE gpu=$gpu'"
  } > "$script"
  chmod +x "$script"
}

mapfile -t gpu_array < <(printf '%s\n' $GPUS)
mapfile -t all_names < "$LOG_DIR/cell_names.txt"

log "TOTAL_RUNS=${#all_names[@]} GPUS=${gpu_array[*]} CONCURRENCY=$CONCURRENCY"

for gpu_idx in "${!gpu_array[@]}"; do
  gpu="${gpu_array[$gpu_idx]}"
  assigned=()
  for idx in "${!all_names[@]}"; do
    if [ $((idx % ${#gpu_array[@]})) -eq "$gpu_idx" ]; then
      assigned+=("${all_names[$idx]}")
    fi
  done
  [ "${#assigned[@]}" -eq 0 ] && continue
  write_queue "$gpu" "${assigned[@]}"
  screen_name="drr_cv_g${gpu}"
  screen -S "$screen_name" -X quit >/dev/null 2>&1 || true
  screen -dmS "$screen_name" bash -c \
    "bash '$LOG_DIR/gpu${gpu}_queue.sh' > '$LOG_DIR/gpu${gpu}_queue.log' 2>&1"
  log "LAUNCHED gpu=$gpu screen=$screen_name runs=${#assigned[@]}"
done

log "ALL_LAUNCHED total=$NUM_RUNS"
screen -ls 2>/dev/null | grep drr_cv || true
