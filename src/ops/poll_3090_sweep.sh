#!/usr/bin/env bash
# Poll sweep status from Windows-side WSL call
# Usage: wsl bash /mnt/c/source/JDCNET/src/ops/poll_3090_sweep.sh
set -e
ENV=/mnt/c/source/.env
HOST=mabo1215@10.147.20.176

ssh_run() {
  SSHPASS=mabo1215 sshpass -e ssh \
    -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR \
    "$HOST" "$@"
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
