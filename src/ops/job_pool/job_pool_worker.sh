#!/usr/bin/env bash
set -euo pipefail

POOL_DIR="${POOL_DIR:-/data/JDCNET/job_pool}"
QUEUE_FILE="$POOL_DIR/queue.txt"
LOCK_FILE="$POOL_DIR/queue.lock"
RUN_PID_FILE="$POOL_DIR/running.pid"
RUN_JOB_FILE="$POOL_DIR/running.job"
LOG_FILE="$POOL_DIR/worker.log"

mkdir -p "$POOL_DIR"
touch "$QUEUE_FILE" "$LOCK_FILE" "$LOG_FILE"

echo "[$(date '+%F %T')] worker started" >> "$LOG_FILE"

while true; do
  # If a running PID exists and is alive, wait.
  if [[ -f "$RUN_PID_FILE" ]]; then
    pid="$(cat "$RUN_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      sleep 5
      continue
    fi
    rm -f "$RUN_PID_FILE" "$RUN_JOB_FILE"
    echo "[$(date '+%F %T')] previous job finished" >> "$LOG_FILE"
  fi

  next_job=""
  exec 9>"$LOCK_FILE"
  flock -x 9
  if [[ -s "$QUEUE_FILE" ]]; then
    next_job="$(head -n 1 "$QUEUE_FILE")"
    tail -n +2 "$QUEUE_FILE" > "$QUEUE_FILE.tmp" && mv "$QUEUE_FILE.tmp" "$QUEUE_FILE"
  fi
  flock -u 9
  exec 9>&-

  if [[ -z "$next_job" ]]; then
    sleep 5
    continue
  fi

  ts="$(date '+%F %T')"
  echo "[$ts] starting job: $next_job" >> "$LOG_FILE"

  # Each queued line is a full shell command.
  bash -lc "$next_job" >> "$LOG_FILE" 2>&1 &
  pid=$!
  echo "$pid" > "$RUN_PID_FILE"
  echo "$next_job" > "$RUN_JOB_FILE"
  echo "[$(date '+%F %T')] pid=$pid" >> "$LOG_FILE"

done
