#!/usr/bin/env bash
# GAP-KD parameter sweep on 3090 — BIMCV pathC as proxy dataset
# Sweeps: gate_threshold in {0.55, 0.60, 0.65}
#         projected_attention_weight in {0.0, 0.02, 0.05}
#         seeds: 42, 43, 44  (3x3x3 = 27 GAP-KD runs)
# Baselines: bimcv_pathc xray_supervised and cross_modal_kd (already done)
# Goal: identify stable hyperparameters that fix seed-43 instability
set -euo pipefail

ROOT=${ROOT:-/data/JDCNET/src}
CFG_DIR="$ROOT/configs/bimcv_gapkd_sweep"
RUN_ROOT="$ROOT/runs/bimcv_gapkd_sweep"
LOG_ROOT=${LOG_ROOT:-/data/logs/bimcv_gapkd_sweep}
MANIFEST="$ROOT/data/bimcv/bimcv_merged_paired_manifest_pathc.csv"
SUMMARY_CSV="$LOG_ROOT/sweep_summary.csv"
STATUS_LOG="$LOG_ROOT/status.tsv"
SEEDS=${SEEDS:-"42 43 44"}
EPOCHS=${EPOCHS:-50}
BATCH_SIZE=${BATCH_SIZE:-16}
INPUT_SIZE=${INPUT_SIZE:-224}
GATE_FLOOR=${GATE_FLOOR:-0.10}

mkdir -p "$CFG_DIR" "$RUN_ROOT" "$LOG_ROOT"

log() { printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS_LOG"; }

done_run() {
  local d="$1"
  [ -s "$d/best_metrics.json" ] && [ -s "$d/best.pt" ]
}

# Generate all configs
python3 - <<PY
import json
import itertools
from pathlib import Path

cfg_dir = Path("$CFG_DIR")
run_root = Path("$RUN_ROOT")
manifest = "$MANIFEST"
epochs = $EPOCHS
batch_size = $BATCH_SIZE
input_size = $INPUT_SIZE
gate_floor = $GATE_FLOOR
seeds = [int(s) for s in "$SEEDS".split()]

thresholds = [0.55, 0.60, 0.65]
proj_weights = [0.0, 0.02, 0.05]

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
base_data = {
    "train_split": "train",
    "val_split": "val",
    "train_modalities": ["xray"],
    "val_modalities": ["xray"],
    "batch_size": batch_size,
    "num_workers": 4,
    "paired_image_column": "teacher_image_path",
    "use_weighted_sampler": True,
}
base_optim = {"epochs": epochs, "learning_rate": 3e-4, "weight_decay": 1e-4}

written = 0
for seed, thr, proj in itertools.product(seeds, thresholds, proj_weights):
    thr_str = f"{int(thr*100):03d}"
    proj_str = f"{int(proj*1000):04d}"
    name = f"bimcv_sweep_thr{thr_str}_proj{proj_str}_s{seed}"
    teacher_ckpt = f"/data/JDCNET/src/runs/bimcv_pathc/bimcv_resnet18_pathc_teacher_ct_s{seed}/best.pt"
    cfg = {
        "experiment_name": name,
        "manifest_path": manifest,
        "output_dir": str(run_root / name),
        "seed": seed,
        "model": base_model,
        "data": base_data,
        "optimization": base_optim,
        "distillation": {
            "enabled": True,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": teacher_ckpt,
            "confidence_gate_enabled": True,
            "confidence_gate_threshold": thr,
            "confidence_gate_floor": gate_floor,
            "confidence_gate_power": 1.0,
            "confidence_gate_requires_correct": True,
            "projected_attention_weight": proj,
        },
    }
    out = cfg_dir / f"{name}.json"
    out.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    written += 1

print(f"[config-gen] wrote {written} configs to {cfg_dir}")
PY

log "CONFIG_GEN_DONE"

# Build queue: skip already-done runs
QUEUE=()
for cfg in "$CFG_DIR"/bimcv_sweep_*.json; do
  name=$(basename "$cfg" .json)
  run_dir="$RUN_ROOT/$name"
  if done_run "$run_dir"; then
    log "SKIP $name"
  else
    QUEUE+=("$name")
  fi
done

log "QUEUE_SIZE=${#QUEUE[@]}"

if [ "${#QUEUE[@]}" -eq 0 ]; then
  log "ALL_DONE"
else
  # Assign round-robin to 4 GPUs; collect PIDs
  GPUS=(0 1 2 3)
  declare -A GPU_PIDS
  declare -A GPU_QUEUE
  for g in "${GPUS[@]}"; do GPU_QUEUE[$g]=""; done

  idx=0
  for name in "${QUEUE[@]}"; do
    gpu="${GPUS[$((idx % 4))]}"
    GPU_QUEUE[$gpu]+=" $name"
    idx=$((idx + 1))
  done

  for gpu in "${GPUS[@]}"; do
    names="${GPU_QUEUE[$gpu]:-}"
    [ -z "$names" ] && continue
    screen_name="gapkd_sweep_g${gpu}"
    screen -S "$screen_name" -X quit >/dev/null 2>&1 || true

    # Build a sequential shell script for this GPU's queue
    gpu_script="$LOG_ROOT/gpu${gpu}_queue.sh"
    {
      echo "#!/usr/bin/env bash"
      echo "set -e"
      echo "cd '$ROOT'"
      for n in $names; do
        run_dir="$RUN_ROOT/$n"
        cfg="$CFG_DIR/${n}.json"
        log_f="$LOG_ROOT/${n}.log"
        echo "echo '[START] $n'"
        echo "if [ -s '$run_dir/best_metrics.json' ]; then echo '[SKIP_DONE] $n'; else"
        echo "  CUDA_VISIBLE_DEVICES=$gpu python3 -m jdcnet_exp.train --config '$cfg' > '$log_f' 2>&1"
        echo "  echo '[DONE] $n'"
        echo "fi"
      done
      echo "echo '[GPU_QUEUE_DONE] gpu=$gpu'"
    } > "$gpu_script"
    chmod +x "$gpu_script"

    screen -dmS "$screen_name" bash "$gpu_script"
    log "LAUNCHED gpu=$gpu screen=$screen_name count=$(echo $names | wc -w)"
  done

  log "ALL_LAUNCHED waiting"
fi

# Print baseline summary for context
echo ""
echo "=== BASELINES (bimcv_pathc) ==="
python3 - <<PY
import json
from pathlib import Path

runs = Path("/data/JDCNET/src/runs/bimcv_pathc")
for tag, pat in [("supervised", "xray_supervised"), ("plain_kd", "xray_cross_modal_kd")]:
    bas = []
    for seed in [42, 43, 44]:
        d = runs / f"bimcv_resnet18_pathc_{pat}_s{seed}"
        bm = d / "best_metrics.json"
        if bm.exists():
            ba = json.loads(bm.read_text()).get("balanced_accuracy", None)
            bas.append(f"s{seed}={ba:.4f}" if ba else f"s{seed}=?")
    print(f"  {tag}: {', '.join(bas)}")
PY

echo ""
echo "=== SCREEN STATUS ==="
screen -ls 2>/dev/null | grep gapkd_sweep || echo "(none running yet)"
echo ""
echo "To monitor: tail -f $LOG_ROOT/gpu0_queue.sh && screen -r gapkd_sweep_g0"
echo "To summarize when done: run remote_3090_gapkd_sweep_summarize.sh"
