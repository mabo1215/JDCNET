#!/usr/bin/env bash
# Poll sweep status from a WSL shell using an SSH key or agent.
# Usage: JDCNET_R3090_SSH_TARGET=<user>@<host> \
#   wsl bash /mnt/c/source/JDCNET/src/ops/poll_3090_sweep.sh
set -euo pipefail

HOST="${JDCNET_R3090_SSH_TARGET:-${SSH_TARGET:-}}"
if [[ -z "${HOST}" ]]; then
  echo "Set JDCNET_R3090_SSH_TARGET to an SSH host or ~/.ssh/config alias." >&2
  exit 2
fi

SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o StrictHostKeyChecking=accept-new
  -o LogLevel=ERROR
)

ssh_run() {
  ssh "${SSH_OPTIONS[@]}" "$HOST" "$@"
}

ssh_run bash <<'REMOTE'
echo "=SCREENS="
screen -ls 2>/dev/null | grep gapkd_sweep || echo "(none)"
echo "=PROGRESS="
done=0; total=0
for d in /data/JDCNET/src/runs/bimcv_gapkd_sweep/*/; do
  total=$((total+1))
  [ -s "$d/best_metrics.json" ] && done=$((done+1))
done
echo "Done: $done / $total"
echo "=GPU="
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null
echo "=LAST_STATUS="
tail -n 10 /data/logs/bimcv_gapkd_sweep/status.tsv 2>/dev/null || echo "(no status log)"
REMOTE
