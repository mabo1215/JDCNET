#!/usr/bin/env bash
set -euo pipefail

POOL_DIR="${POOL_DIR:-/data/JDCNET/job_pool}"
QUEUE_FILE="$POOL_DIR/queue.txt"
LOCK_FILE="$POOL_DIR/queue.lock"

mkdir -p "$POOL_DIR"
touch "$QUEUE_FILE" "$LOCK_FILE"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 '<command>'"
  exit 1
fi

job="$*"

exec 9>"$LOCK_FILE"
flock -x 9
printf '%s\n' "$job" >> "$QUEUE_FILE"
count="$(wc -l < "$QUEUE_FILE" | tr -d ' ')"
flock -u 9
exec 9>&-

echo "ENQUEUED: $job"
echo "QUEUE_LENGTH: $count"
