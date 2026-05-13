#!/usr/bin/env bash
set -euo pipefail

echo "SCREEN:"
screen -ls 2>/dev/null | grep midrc_559_combined_dl || true

echo "PROC:"
pgrep -af "/data/tools/gen3-client.*download-multiple" || true

echo "FILES:"
find /data1/midrc/raw_559cases_combined -type f 2>/dev/null | wc -l

echo "RECENT10:"
find /data1/midrc/raw_559cases_combined -type f -mmin -10 2>/dev/null | wc -l

echo "LASTLOG:"
latest=$(ls -t /data1/logs/midrc/midrc_559_download_restarted_*.log 2>/dev/null | head -1 || true)
if [[ -n "$latest" ]]; then
  echo "$latest"
  tail -n 30 "$latest" || true
else
  echo "NO_RESTART_LOG"
fi
