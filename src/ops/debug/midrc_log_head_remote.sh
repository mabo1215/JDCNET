#!/usr/bin/env bash
set -euo pipefail
latest=$(ls -t /data1/logs/midrc/midrc_559_download_restarted_*.log 2>/dev/null | head -1 || true)
echo "LOG:$latest"
if [[ -n "$latest" ]]; then
  head -n 30 "$latest" || true
fi
