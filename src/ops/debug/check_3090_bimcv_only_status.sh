#!/usr/bin/env bash
set -euo pipefail

MODE=${MODE:-balanced}
LOG_DIR=${LOG_DIR:-/data1/logs/bimcv_only_5fold_cv_3090_${MODE}}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/bimcv_only_5fold_cv_${MODE}}

echo "=== TIME ==="
date -Is
echo "=== GPU ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits 2>&1 || true
echo "=== SCREENS ==="
screen -ls 2>&1 | grep "bimcv5f_${MODE}" || true
echo "=== STATUS ==="
tail -n 40 "$LOG_DIR/status.tsv" 2>/dev/null || true
echo "=== COUNTS ==="
total=$(find "$RUN_ROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
best=$(find "$RUN_ROOT" -mindepth 2 -maxdepth 2 -name best_metrics.json 2>/dev/null | wc -l | tr -d ' ')
test=$(find "$RUN_ROOT" -mindepth 3 -maxdepth 3 -path '*/test_eval/metrics.json' 2>/dev/null | wc -l | tr -d ' ')
echo "run_dirs=$total best_metrics=$best test_metrics=$test"
echo "=== RECENT ERRORS ==="
grep -R "CUDA out of memory\\|Traceback\\|FileNotFoundError\\|Killed\\|RuntimeError" "$LOG_DIR" 2>/dev/null | tail -n 30 || true
