#!/usr/bin/env bash
set -euo pipefail

echo "COUNT:"
find /data1/midrc/raw_559cases_combined -type f 2>/dev/null | wc -l

echo "RECENT10:"
find /data1/midrc/raw_559cases_combined -type f -mmin -10 2>/dev/null | wc -l

echo "SCREEN:"
screen -ls 2>/dev/null | grep midrc_559_combined_dl || true

echo "PROC:"
pgrep -af "/data/tools/gen3-client.*download-multiple" || true

echo "LOGS:"
ls -lt /data1/logs/midrc/midrc_559_download_restarted_*.log 2>/dev/null | head -3 || true
