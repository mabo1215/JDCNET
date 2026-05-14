#!/usr/bin/env bash
set -euo pipefail

# Four-GPU BIMCV-only same-source DRR/X-ray CV launcher for the 3090 host.
# Each GPU receives a sequential queue of fold/seed tuples.  A tuple trains:
#   teacher DRR -> X-ray supervised -> plain KD -> reliability-gated KD,
# followed by test-split evaluation for each row.

ROOT=${ROOT:-/data/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
BIMCV_MANIFEST=${BIMCV_MANIFEST:-$ROOT/data/bimcv/bimcv_merged_paired_manifest_pathc.csv}
CV_DIR=${CV_DIR:-/data1/midrc/bimcv_only_cv_20260514}
MODE=${MODE:-balanced}
CV_SEED=${CV_SEED:-99}
PREFIX=${PREFIX:-bimcv_only}

RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/bimcv_only_5fold_cv_${MODE}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/bimcv_only_5fold_cv_${MODE}}
LOG_DIR=${LOG_DIR:-/data1/logs/bimcv_only_5fold_cv_3090_${MODE}}

FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
GPUS=${GPUS:-"0 1 2 3"}
EPOCHS=${EPOCHS:-50}
TEACHER_EPOCHS=${TEACHER_EPOCHS:-30}
INPUT_SIZE=${INPUT_SIZE:-224}
BATCH_SIZE=${BATCH_SIZE:-128}
TEACHER_BATCH_SIZE=${TEACHER_BATCH_SIZE:-$BATCH_SIZE}
NUM_WORKERS=${NUM_WORKERS:-16}
PREFETCH_FACTOR=${PREFETCH_FACTOR:-4}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-false}
VALIDATION_INTERVAL=${VALIDATION_INTERVAL:-1}
USE_WEIGHTED_SAMPLER=${USE_WEIGHTED_SAMPLER:-true}

GATE_THRESHOLD=${GATE_THRESHOLD:-0.55}
GATE_FLOOR=${GATE_FLOOR:-0.0}
TEMPERATURE=${TEMPERATURE:-4.0}
ALPHA=${ALPHA:-0.6}

mkdir -p "$CV_DIR" "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR"
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

log "START mode=$MODE folds=[$FOLDS] seeds=[$SEEDS] batch=$BATCH_SIZE teacher_batch=$TEACHER_BATCH_SIZE workers=$NUM_WORKERS"

if [ ! -s "$CV_DIR/${PREFIX}_summary.json" ]; then
  log "PREPARE_CV_MANIFESTS"
  "$PYTHON_BIN" -u -m jdcnet_exp.prepare_bimcv_only_cv \
    --bimcv-manifest "$BIMCV_MANIFEST" \
    --output-dir "$CV_DIR" \
    --prefix "$PREFIX" \
    --folds 5 \
    --seed "$CV_SEED" \
    --mode "$MODE" \
    --require-existing-paths \
    > "$LOG_DIR/prepare_cv.log" 2>&1
else
  log "SKIP_PREPARE existing=$CV_DIR/${PREFIX}_summary.json"
fi

export ROOT RUN_ROOT CONFIG_DIR CV_DIR PREFIX FOLDS SEEDS EPOCHS TEACHER_EPOCHS INPUT_SIZE BATCH_SIZE \
  TEACHER_BATCH_SIZE NUM_WORKERS PREFETCH_FACTOR AMP CHANNELS_LAST TORCH_COMPILE VALIDATION_INTERVAL \
  USE_WEIGHTED_SAMPLER GATE_THRESHOLD GATE_FLOOR TEMPERATURE ALPHA

"$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
config_dir = Path(os.environ["CONFIG_DIR"])
cv_dir = Path(os.environ["CV_DIR"])
prefix = os.environ["PREFIX"]
folds = [int(x) for x in os.environ["FOLDS"].split()]
seeds = [int(x) for x in os.environ["SEEDS"].split()]
epochs = int(os.environ["EPOCHS"])
teacher_epochs = int(os.environ["TEACHER_EPOCHS"])
input_size = int(os.environ["INPUT_SIZE"])
batch_size = int(os.environ["BATCH_SIZE"])
teacher_batch_size = int(os.environ["TEACHER_BATCH_SIZE"])
num_workers = int(os.environ["NUM_WORKERS"])
prefetch_factor = int(os.environ["PREFETCH_FACTOR"])
amp = os.environ["AMP"].lower() == "true"
channels_last = os.environ["CHANNELS_LAST"].lower() == "true"
torch_compile = os.environ["TORCH_COMPILE"].lower() == "true"
validation_interval = int(os.environ["VALIDATION_INTERVAL"])
weighted = os.environ["USE_WEIGHTED_SAMPLER"].lower() == "true"
gate_threshold = float(os.environ["GATE_THRESHOLD"])
gate_floor = float(os.environ["GATE_FLOOR"])
temperature = float(os.environ["TEMPERATURE"])
alpha = float(os.environ["ALPHA"])

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

def data_cfg(batch: int, train_modalities: list[str], val_modalities: list[str]) -> dict:
    return {
        "train_split": "train",
        "val_split": "val",
        "train_modalities": train_modalities,
        "val_modalities": val_modalities,
        "batch_size": batch,
        "num_workers": num_workers,
        "paired_image_column": "teacher_image_path",
        "use_weighted_sampler": weighted,
        "pin_memory": True,
        "persistent_workers": num_workers > 0,
        "prefetch_factor": prefetch_factor,
    }

def optim_cfg(n_epochs: int) -> dict:
    return {
        "epochs": n_epochs,
        "learning_rate": 3e-4,
        "weight_decay": 1e-4,
        "grad_accum_steps": 1,
        "amp": amp,
        "channels_last": channels_last,
        "torch_compile": torch_compile,
        "validation_interval": validation_interval,
    }

no_distill = {"enabled": False, "temperature": temperature, "alpha": alpha, "teacher_checkpoint": ""}

written = 0
for fold in folds:
    fold_dir = cv_dir / f"fold_{fold:02d}"
    paired_manifest = str((fold_dir / f"{prefix}_fold{fold:02d}_paired_manifest.csv").resolve())
    ct_manifest = str((fold_dir / f"{prefix}_fold{fold:02d}_ct_manifest.csv").resolve())
    for seed in seeds:
        tag = f"f{fold:02d}_s{seed}"
        teacher_name = f"bimcv_only_{tag}_teacher_drr"
        teacher_dir = run_root / teacher_name
        teacher_cfg = {
            "experiment_name": teacher_name,
            "manifest_path": ct_manifest,
            "output_dir": str(teacher_dir),
            "seed": seed,
            "model": {**base_model, "name": "teacher"},
            "data": data_cfg(teacher_batch_size, ["ct"], ["ct"]),
            "optimization": optim_cfg(teacher_epochs),
            "distillation": no_distill,
        }
        (config_dir / f"{teacher_name}.json").write_text(json.dumps(teacher_cfg, indent=2), encoding="utf-8")
        written += 1

        sup_name = f"bimcv_only_{tag}_xray_supervised"
        sup_cfg = {
            "experiment_name": sup_name,
            "manifest_path": paired_manifest,
            "output_dir": str(run_root / sup_name),
            "seed": seed,
            "model": base_model,
            "data": data_cfg(batch_size, ["xray"], ["xray"]),
            "optimization": optim_cfg(epochs),
            "distillation": no_distill,
        }
        (config_dir / f"{sup_name}.json").write_text(json.dumps(sup_cfg, indent=2), encoding="utf-8")
        written += 1

        plain_name = f"bimcv_only_{tag}_plain_kd"
        plain_cfg = {
            **sup_cfg,
            "experiment_name": plain_name,
            "output_dir": str(run_root / plain_name),
            "distillation": {
                "enabled": True,
                "temperature": temperature,
                "alpha": alpha,
                "teacher_checkpoint": str(teacher_dir / "best.pt"),
            },
        }
        (config_dir / f"{plain_name}.json").write_text(json.dumps(plain_cfg, indent=2), encoding="utf-8")
        written += 1

        gated_name = f"bimcv_only_{tag}_gated_kd_thr{int(round(gate_threshold*100)):03d}_proj0000"
        gated_cfg = {
            **sup_cfg,
            "experiment_name": gated_name,
            "output_dir": str(run_root / gated_name),
            "distillation": {
                "enabled": True,
                "temperature": temperature,
                "alpha": alpha,
                "teacher_checkpoint": str(teacher_dir / "best.pt"),
                "confidence_gate_enabled": True,
                "confidence_gate_threshold": gate_threshold,
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
        (config_dir / f"{gated_name}.json").write_text(json.dumps(gated_cfg, indent=2), encoding="utf-8")
        written += 1

print(f"wrote {written} configs to {config_dir}")
PY

write_queue_script() {
  local gpu="$1"; shift
  local tuples=("$@")
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
    for tuple in "${tuples[@]}"; do
      IFS=: read -r fold seed <<< "$tuple"
      local tag="f$(printf '%02d' "$fold")_s${seed}"
      local teacher="bimcv_only_${tag}_teacher_drr"
      local sup="bimcv_only_${tag}_xray_supervised"
      local plain="bimcv_only_${tag}_plain_kd"
      local gated="bimcv_only_${tag}_gated_kd_thr$(printf '%03d' "$(python3 - <<PY
print(int(round(float("$GATE_THRESHOLD")*100)))
PY
)")_proj0000"
      for name in "$teacher" "$sup" "$plain" "$gated"; do
        echo "name='$name'; cfg='$CONFIG_DIR/$name.json'; run_dir='$RUN_ROOT/$name'; log_f='$LOG_DIR/$name.log'"
        echo "if done_run \"\$run_dir\"; then log \"SKIP_DONE \$name\"; else log \"START gpu=$gpu \$name\"; CUDA_VISIBLE_DEVICES=$gpu '$PYTHON_BIN' -u -m jdcnet_exp.train --config \"\$cfg\" > \"\$log_f\" 2>&1; log \"DONE gpu=$gpu \$name\"; fi"
        echo "eval_test \"\$name\""
      done
    done
    echo "log 'GPU_QUEUE_DONE gpu=$gpu'"
  } > "$script"
  chmod +x "$script"
  : > "$queue_log"
}

mapfile -t gpu_array < <(printf '%s\n' $GPUS)
tuple_list=()
for fold in $FOLDS; do
  for seed in $SEEDS; do
    tuple_list+=("${fold}:${seed}")
  done
done

log "TUPLES=${#tuple_list[@]} GPUS=${gpu_array[*]}"

for gpu in "${gpu_array[@]}"; do
  assigned=()
  for idx in "${!tuple_list[@]}"; do
    if [ $((idx % ${#gpu_array[@]})) -eq "$gpu" ]; then
      assigned+=("${tuple_list[$idx]}")
    fi
  done
  if [ "${#assigned[@]}" -eq 0 ]; then
    continue
  fi
  write_queue_script "$gpu" "${assigned[@]}"
  screen_name="bimcv5f_${MODE}_g${gpu}"
  screen -S "$screen_name" -X quit >/dev/null 2>&1 || true
  screen -dmS "$screen_name" bash "$LOG_DIR/gpu${gpu}_queue.sh"
  log "LAUNCHED gpu=$gpu screen=$screen_name tuples=${#assigned[@]}"
done

log "ALL_LAUNCHED"
screen -ls 2>/dev/null | grep "bimcv5f_${MODE}" || true
