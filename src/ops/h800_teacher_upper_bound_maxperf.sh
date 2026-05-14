#!/usr/bin/env bash
set -euo pipefail

# High-throughput launcher for MIDRC teacher upper-bound priority stage.
#
# Strategy:
# 1) Run one baseline pack (teacher + xray supervised) for the first variant.
# 2) Run remaining teacher variants in teacher-only mode, optionally in parallel,
#    to push GPU utilization higher on 80GB cards.

REPO=${REPO:-/root/autodl-tmp/JDCNET/src}
BASE_OUT=${BASE_OUT:-/root/autodl-tmp/midrc/locked_validation}
BASE_LOG=${BASE_LOG:-/root/autodl-tmp/logs/midrc_teacher_upper_bound_maxperf}
BASE_RUN=${BASE_RUN:-/root/autodl-tmp/runs/midrc_teacher_upper_bound_maxperf}
BASE_CFG=${BASE_CFG:-/root/autodl-tmp/JDCNET/src/configs/midrc_teacher_upper_bound_maxperf}
SEEDS=${SEEDS:-42 43 44}
EPOCHS=${EPOCHS:-30}
BATCH_SIZE=${BATCH_SIZE:-160}
NUM_WORKERS=${NUM_WORKERS:-16}
INPUT_SIZE=${INPUT_SIZE:-224}
MAX_PARALLEL_VARIANTS=${MAX_PARALLEL_VARIANTS:-2}
AUTO_SHUTDOWN=${AUTO_SHUTDOWN:-0}

mkdir -p "$BASE_LOG" "$BASE_RUN" "$BASE_CFG"
cd "$REPO"

variants=(
  ct_3slice_lung_rgb
  ct_5slice_lung_montage
  ct_9slice_lung_montage
  ct_multiwindow_mid_rgb
  ct_mean_projection_lung
  ct_mip_lung
)

variant_manifest() {
  local v="$1"
  echo "/root/autodl-tmp/midrc/teacher_variants_20260513/midrc_upper_bound_${v}_ct_manifest.csv"
}

run_pack() {
  local variant="$1"
  local mode="$2"
  local tag="${variant}"

  local run_root="$BASE_RUN/$tag"
  local log_dir="$BASE_LOG/$tag"
  local cfg_dir="$BASE_CFG/$tag"

  mkdir -p "$run_root" "$log_dir" "$cfg_dir"

  echo "[$(date -Is)] START variant=$variant mode=$mode"
  RUN_MODE="$mode" \
  TEACHER_CT_MANIFEST="$(variant_manifest "$variant")" \
  REPO="$REPO" \
  OUT="$BASE_OUT" \
  RUN_ROOT="$run_root" \
  LOG_DIR="$log_dir" \
  CONFIG_DIR="$cfg_dir" \
  SEEDS="$SEEDS" \
  EPOCHS="$EPOCHS" \
  BATCH_SIZE="$BATCH_SIZE" \
  NUM_WORKERS="$NUM_WORKERS" \
  INPUT_SIZE="$INPUT_SIZE" \
  OPT_AMP=1 OPT_CHANNELS_LAST=1 OPT_TORCH_COMPILE=1 \
  AUTO_SHUTDOWN="$AUTO_SHUTDOWN" \
  bash "$REPO/ops/h800_midrc_locked_validation.sh"
  echo "[$(date -Is)] DONE variant=$variant mode=$mode"
}

# 1) Baseline + first teacher variant.
run_pack "${variants[0]}" "teacher_supervised_only"

# 2) Remaining teacher variants in parallel (teacher-only).
pids=()
for variant in "${variants[@]:1}"; do
  while [ "$(jobs -pr | wc -l)" -ge "$MAX_PARALLEL_VARIANTS" ]; do
    sleep 10
  done
  run_pack "$variant" "teacher_only" > "$BASE_LOG/${variant}.driver.log" 2>&1 &
  pids+=("$!")
done

for pid in "${pids[@]}"; do
  wait "$pid"
done

echo "[$(date -Is)] ALL teacher upper-bound packs finished"
