#!/usr/bin/env bash
set -euo pipefail

POOL_DIR="${POOL_DIR:-/data/JDCNET/job_pool}"
QUEUE_FILE="$POOL_DIR/queue.txt"
RUN_PID_FILE="$POOL_DIR/running.pid"
RUN_JOB_FILE="$POOL_DIR/running.job"
LOG_FILE="$POOL_DIR/worker.log"

echo "POOL_DIR=$POOL_DIR"

if [[ -f "$RUN_PID_FILE" ]]; then
  pid="$(cat "$RUN_PID_FILE" 2>/dev/null || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "RUNNING_PID=$pid"
    echo -n "RUNNING_JOB="
    cat "$RUN_JOB_FILE" 2>/dev/null || true
  else
    echo "RUNNING_PID=none"
  fi
else
  echo "RUNNING_PID=none"
fi

if [[ -f "$QUEUE_FILE" ]]; then
  echo "QUEUE_LENGTH=$(wc -l < "$QUEUE_FILE" | tr -d ' ')"
  echo "QUEUE_HEAD:"
  head -n 5 "$QUEUE_FILE" || true
else
  echo "QUEUE_LENGTH=0"
fi

echo "WORKER_LOG_TAIL:"
tail -n 20 "$LOG_FILE" 2>/dev/null || true
