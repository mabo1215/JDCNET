#!/usr/bin/env bash
set -euo pipefail

# BIMCV-only Priority-2 calibration scan for the 3090 host.
#
# Sweeps (temperature, confidence_gate_threshold) for the reliability-gated
# KD row only.  Re-uses the teacher_drr and xray_supervised checkpoints from
# the earlier remote_3090_bimcv_only_5fold_cv.sh run (RUN_ROOT_BASE below) so
# the scan trains a single new student per (fold, seed, T, thr) cell.
#
# Grid default: T in {2,4,8} x thr in {0.50,0.55,0.60} = 9 cells.
# The cell (T=4.0, thr=0.55) is skipped because it is already reported.
# 8 new cells x 5 folds x 3 seeds = 120 new student runs.
#
# GPUs default to "2 3" because GPUs 0/1 are co-tenanted on the 3090 host.

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}

# CV manifests prepared by remote_3090_bimcv_only_5fold_cv.sh
CV_DIR=${CV_DIR:-/data1/midrc/bimcv_only_cv_20260514}
PREFIX=${PREFIX:-bimcv_only}

# Teacher/supervised checkpoints from the earlier run
RUN_ROOT_BASE=${RUN_ROOT_BASE:-/data1/midrc/runs/bimcv_only_5fold_cv_balanced}

# Scan outputs
SCAN_TAG=${SCAN_TAG:-bimcv_only_calibration_scan_20260514}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${SCAN_TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${SCAN_TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${SCAN_TAG}}

FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
T_LIST=${T_LIST:-"2.0 4.0 8.0"}
THR_LIST=${THR_LIST:-"0.50 0.55 0.60"}
# Cell to skip because it is already reported in the prior BIMCV-only CV.
SKIP_CELL=${SKIP_CELL:-"4.0:0.55"}

GPUS=${GPUS:-"2 3"}
EPOCHS=${EPOCHS:-50}
INPUT_SIZE=${INPUT_SIZE:-224}
BATCH_SIZE=${BATCH_SIZE:-256}
NUM_WORKERS=${NUM_WORKERS:-24}
PREFETCH_FACTOR=${PREFETCH_FACTOR:-4}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-false}
VALIDATION_INTERVAL=${VALIDATION_INTERVAL:-1}
USE_WEIGHTED_SAMPLER=${USE_WEIGHTED_SAMPLER:-true}
ALPHA=${ALPHA:-0.6}
GATE_FLOOR=${GATE_FLOOR:-0.0}

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR"
STATUS="$LOG_DIR/status.tsv"
touch "$STATUS"

log() {
  printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"
}

done_run() {
  local d="$1"
  [ -s "$d/best_metrics.json" ] && [ -s "$d/best.pt" ]
}

done_test_eval() {
  local d="$1"
  [ -s "$d/test_eval/metrics.json" ]
}

cd "$ROOT"

log "SCAN_START folds=[$FOLDS] seeds=[$SEEDS] T=[$T_LIST] thr=[$THR_LIST] skip=$SKIP_CELL gpus=[$GPUS]"

if [ ! -s "$CV_DIR/${PREFIX}_summary.json" ]; then
  log "FATAL CV manifests missing at $CV_DIR; run remote_3090_bimcv_only_5fold_cv.sh first"
  exit 1
fi

export ROOT RUN_ROOT_BASE RUN_ROOT CONFIG_DIR CV_DIR LOG_DIR PREFIX FOLDS SEEDS T_LIST THR_LIST SKIP_CELL \
  EPOCHS INPUT_SIZE BATCH_SIZE NUM_WORKERS PREFETCH_FACTOR AMP CHANNELS_LAST TORCH_COMPILE \
  VALIDATION_INTERVAL USE_WEIGHTED_SAMPLER ALPHA GATE_FLOOR

"$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
run_root_base = Path(os.environ["RUN_ROOT_BASE"])
config_dir = Path(os.environ["CONFIG_DIR"])
cv_dir = Path(os.environ["CV_DIR"])
prefix = os.environ["PREFIX"]

folds = [int(x) for x in os.environ["FOLDS"].split()]
seeds = [int(x) for x in os.environ["SEEDS"].split()]
t_list = [float(x) for x in os.environ["T_LIST"].split()]
thr_list = [float(x) for x in os.environ["THR_LIST"].split()]
skip_cells = set()
for tok in os.environ["SKIP_CELL"].split(","):
    tok = tok.strip()
    if not tok:
        continue
    t_s, thr_s = tok.split(":")
    skip_cells.add((round(float(t_s), 4), round(float(thr_s), 4)))

epochs = int(os.environ["EPOCHS"])
input_size = int(os.environ["INPUT_SIZE"])
batch_size = int(os.environ["BATCH_SIZE"])
num_workers = int(os.environ["NUM_WORKERS"])
prefetch_factor = int(os.environ["PREFETCH_FACTOR"])
amp = os.environ["AMP"].lower() == "true"
channels_last = os.environ["CHANNELS_LAST"].lower() == "true"
torch_compile = os.environ["TORCH_COMPILE"].lower() == "true"
validation_interval = int(os.environ["VALIDATION_INTERVAL"])
weighted = os.environ["USE_WEIGHTED_SAMPLER"].lower() == "true"
alpha = float(os.environ["ALPHA"])
gate_floor = float(os.environ["GATE_FLOOR"])

base_model = {
    "name": "student",
    "num_classes": 2,
    "input_size": input_size,
    "use_dpe": False,
    "use_mhra": False,
    "use_dfpn": False,
    "paired_input": False,
    "backbone": "resnet18",
}


def data_cfg(batch: int) -> dict:
    return {
        "train_split": "train",
        "val_split": "val",
        "train_modalities": ["xray"],
        "val_modalities": ["xray"],
        "batch_size": batch,
        "num_workers": num_workers,
        "paired_image_column": "teacher_image_path",
        "use_weighted_sampler": weighted,
        "pin_memory": True,
        "persistent_workers": num_workers > 0,
        "prefetch_factor": prefetch_factor,
    }


def optim_cfg() -> dict:
    return {
        "epochs": epochs,
        "learning_rate": 3e-4,
        "weight_decay": 1e-4,
        "grad_accum_steps": 1,
        "amp": amp,
        "channels_last": channels_last,
        "torch_compile": torch_compile,
        "validation_interval": validation_interval,
    }


written = 0
missing_teachers = []
cell_names = []

for fold in folds:
    fold_dir = cv_dir / f"fold_{fold:02d}"
    paired_manifest = str((fold_dir / f"{prefix}_fold{fold:02d}_paired_manifest.csv").resolve())
    for seed in seeds:
        teacher_ckpt = run_root_base / f"{prefix}_f{fold:02d}_s{seed}_teacher_drr" / "best.pt"
        if not teacher_ckpt.exists():
            missing_teachers.append(str(teacher_ckpt))
            continue
        for t in t_list:
            for thr in thr_list:
                if (round(t, 4), round(thr, 4)) in skip_cells:
                    continue
                t_tag = f"t{int(round(t*10)):03d}"
                thr_tag = f"thr{int(round(thr*100)):03d}"
                tag = f"f{fold:02d}_s{seed}"
                name = f"calib_{tag}_gated_kd_{t_tag}_{thr_tag}_proj0000"
                cfg = {
                    "experiment_name": name,
                    "manifest_path": paired_manifest,
                    "output_dir": str(run_root / name),
                    "seed": seed,
                    "model": base_model,
                    "data": data_cfg(batch_size),
                    "optimization": optim_cfg(),
                    "distillation": {
                        "enabled": True,
                        "temperature": t,
                        "alpha": alpha,
                        "teacher_checkpoint": str(teacher_ckpt),
                        "confidence_gate_enabled": True,
                        "confidence_gate_threshold": thr,
                        "confidence_gate_floor": gate_floor,
                        "confidence_gate_power": 1.0,
                        "confidence_gate_requires_correct": True,
                        "confidence_gate_positive_threshold": -1.0,
                        "confidence_gate_negative_threshold": -1.0,
                        "confidence_gate_min_margin": 0.0,
                        "confidence_gate_max_entropy": -1.0,
                        "projected_attention_weight": 0.0,
                    },
                }
                (config_dir / f"{name}.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                cell_names.append(name)
                written += 1

print(f"wrote {written} configs to {config_dir}")
print(f"cells: {len(cell_names)} runs")
if missing_teachers:
    print("WARNING missing teacher checkpoints:")
    for p in missing_teachers:
        print(f"  {p}")
manifest_path = Path(os.environ["LOG_DIR"]) / "cell_names.txt"
manifest_path.write_text("\n".join(cell_names) + "\n", encoding="utf-8")
PY

if [ ! -s "$LOG_DIR/cell_names.txt" ]; then
  log "FATAL no cells generated; aborting"
  exit 1
fi

NUM_CELLS=$(wc -l < "$LOG_DIR/cell_names.txt")
log "GENERATED_CELLS=$NUM_CELLS configs=$CONFIG_DIR"

write_queue_script() {
  local gpu="$1"; shift
  local names=("$@")
  local script="$LOG_DIR/gpu${gpu}_queue.sh"
  local queue_log="$LOG_DIR/gpu${gpu}_queue.log"
  {
    echo "#!/usr/bin/env bash"
    echo "set -euo pipefail"
    echo "cd '$ROOT'"
    echo "STATUS='$STATUS'"
    echo 'log(){ printf '"'"'%s\t%s\n'"'"' "$(date -Is)" "$*" | tee -a "$STATUS"; }'
    echo 'done_run(){ [ -s "$1/best_metrics.json" ] && [ -s "$1/best.pt" ]; }'
    echo 'done_test_eval(){ [ -s "$1/test_eval/metrics.json" ]; }'
    echo "eval_test(){ local name=\"\$1\"; local cfg='$CONFIG_DIR'/\"\${name}.json\"; local run_dir='$RUN_ROOT'/\"\${name}\"; local test_cfg='$CONFIG_DIR'/\"\${name}.test.json\"; python3 - \"\$cfg\" \"\$test_cfg\" <<'PY'"
    cat <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
payload = json.load(open(src, encoding="utf-8"))
payload["data"] = dict(payload["data"])
payload["data"]["val_split"] = "test"
json.dump(payload, open(dst, "w", encoding="utf-8"), indent=2)
PY
    echo "PY"
    echo "  if done_test_eval \"\$run_dir\"; then log \"SKIP_TEST_EVAL \$name\"; else CUDA_VISIBLE_DEVICES=$gpu python3 -m jdcnet_exp.evaluate --config \"\$test_cfg\" --checkpoint \"\$run_dir/best.pt\" --output-dir \"\$run_dir/test_eval\" > '$LOG_DIR'/\"\${name}.test_eval.log\" 2>&1; log \"DONE_TEST_EVAL \$name\"; fi; }"
    for name in "${names[@]}"; do
      echo "name='$name'; cfg='$CONFIG_DIR/$name.json'; run_dir='$RUN_ROOT/$name'; log_f='$LOG_DIR/$name.log'"
      echo "if done_run \"\$run_dir\"; then log \"SKIP_DONE \$name\"; else log \"START gpu=$gpu \$name\"; CUDA_VISIBLE_DEVICES=$gpu '$PYTHON_BIN' -u -m jdcnet_exp.train --config \"\$cfg\" > \"\$log_f\" 2>&1; log \"DONE gpu=$gpu \$name\"; fi"
      echo "eval_test \"\$name\""
    done
    echo "log 'GPU_QUEUE_DONE gpu=$gpu'"
  } > "$script"
  chmod +x "$script"
  : > "$queue_log"
}

mapfile -t gpu_array < <(printf '%s\n' $GPUS)
mapfile -t all_names < "$LOG_DIR/cell_names.txt"

log "TUPLES=${#all_names[@]} GPUS=${gpu_array[*]}"

for gpu_idx in "${!gpu_array[@]}"; do
  gpu="${gpu_array[$gpu_idx]}"
  assigned=()
  for idx in "${!all_names[@]}"; do
    if [ $((idx % ${#gpu_array[@]})) -eq "$gpu_idx" ]; then
      assigned+=("${all_names[$idx]}")
    fi
  done
  if [ "${#assigned[@]}" -eq 0 ]; then
    continue
  fi
  write_queue_script "$gpu" "${assigned[@]}"
  screen_name="bimcv_calib_g${gpu}"
  screen -S "$screen_name" -X quit >/dev/null 2>&1 || true
  screen -dmS "$screen_name" bash -c "bash '$LOG_DIR/gpu${gpu}_queue.sh' > '$LOG_DIR/gpu${gpu}_queue.log' 2>&1"
  log "LAUNCHED gpu=$gpu screen=$screen_name cells=${#assigned[@]}"
done

log "ALL_LAUNCHED"
screen -ls 2>/dev/null | grep "bimcv_calib" || true
