#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="${SRC_DIR:-/root/autodl-tmp/JDCNET/src}"
OUT_DIR="${OUT_DIR:-/root/autodl-tmp/bimcv_neg_paired}"
SLICE_DIR="${SLICE_DIR:-/root/autodl-tmp/bimcv_neg_ct_slices}"
LOG_DIR="${LOG_DIR:-/root/autodl-tmp}"
DOWNLOAD_LOG="${DOWNLOAD_LOG:-$LOG_DIR/logs_neg.log}"
PIPELINE_LOG="${PIPELINE_LOG:-$LOG_DIR/h800_bimcv_neg_pipeline.log}"
TARGET_SUBJECTS="${TARGET_SUBJECTS:-398}"
MAX_RESTARTS="${MAX_RESTARTS:-20}"
PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/bin/python3}"
SHARE_TOKEN="${SHARE_TOKEN:-BIMCV-COVID19-cIter_1_2-Negative}"

export PYTHONPATH="$SRC_DIR"
export PYTHONUNBUFFERED=1

count_subjects() {
  find "$OUT_DIR" -maxdepth 1 -type d -name "sub-S*" 2>/dev/null | wc -l
}

download_running() {
  pgrep -f "jdcnet_exp.download_bimcv_neg_paired.*$OUT_DIR" >/dev/null 2>&1
}

log_msg() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$PIPELINE_LOG"
}

mkdir -p "$OUT_DIR" "$SLICE_DIR" "$LOG_DIR" "$SRC_DIR/results"
cd "$SRC_DIR"

restart=0
while true; do
  count="$(count_subjects)"
  log_msg "negative subjects: $count/$TARGET_SUBJECTS"
  if [ "$count" -ge "$TARGET_SUBJECTS" ]; then
    break
  fi
  if [ "$restart" -ge "$MAX_RESTARTS" ]; then
    log_msg "stopping: reached MAX_RESTARTS=$MAX_RESTARTS before full download"
    exit 2
  fi
  if download_running; then
    log_msg "download already running; waiting 300 seconds"
    sleep 300
    continue
  fi
  restart=$((restart + 1))
  log_msg "starting download attempt $restart/$MAX_RESTARTS"
  "$PYTHON_BIN" -u -m jdcnet_exp.download_bimcv_neg_paired \
    --output-dir "$OUT_DIR" \
    --share-token "$SHARE_TOKEN" >> "$DOWNLOAD_LOG" 2>&1 || true
  sleep 60
done

log_msg "download complete; preparing negative manifest"
"$PYTHON_BIN" -u -m jdcnet_exp.prepare_bimcv_neg_dataset \
  --bimcv-root "$OUT_DIR" \
  --output-dir "$SRC_DIR/data/bimcv" \
  --slice-dir "$SLICE_DIR" >> "$PIPELINE_LOG" 2>&1

log_msg "running negative-only readiness gate"
"$PYTHON_BIN" -u -m jdcnet_exp.data_readiness_gate \
  --manifest "$SRC_DIR/data/bimcv/bimcv_neg_manifest.csv" \
  --dataset-name bimcv_negative_only \
  --min-total-patients 20 \
  --min-pos-patients 0 \
  --min-neg-patients 20 \
  --min-val-neg-patients 5 \
  --min-val-total-patients 5 \
  --output "$SRC_DIR/results/bimcv_neg_readiness_gate.json" >> "$PIPELINE_LOG" 2>&1

log_msg "pipeline complete"
