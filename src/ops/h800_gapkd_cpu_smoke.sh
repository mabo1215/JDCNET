#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-/root/autodl-tmp/JDCNET}"
LOG_DIR="/root/autodl-tmp/logs/gapkd_cpu_smoke"
RESULT_DIR="/root/autodl-tmp/results/gapkd_cpu_smoke"
if [ -z "${PYTHON_BIN:-}" ]; then
  for candidate in /root/miniconda3/bin/python3.12 /root/miniconda3/bin/python /usr/bin/python3 python3 python; do
    if [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [ -z "${PYTHON_BIN:-}" ]; then
  echo "No usable Python interpreter found." >&2
  exit 127
fi

mkdir -p "$LOG_DIR" "$RESULT_DIR"
cd "$REPO_ROOT/src"
export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"

{
  echo "START $(date -Iseconds)"
  echo "REPO_ROOT=$REPO_ROOT"
  echo "PYTHON_BIN=$PYTHON_BIN"
  "$PYTHON_BIN" -m jdcnet_exp.smoke_gapkd \
    --output-json "$RESULT_DIR/smoke_gapkd.json"
  echo "DONE $(date -Iseconds)"
} 2>&1 | tee "$LOG_DIR/smoke.log"
