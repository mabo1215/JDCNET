#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=/data1/logs/midrc
DL_ROOT=/data1/midrc/raw_559cases_combined
MANIFEST=/data/secure/midrc/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json
BIN=/data/tools/gen3-client
mkdir -p "$LOG_DIR" "$DL_ROOT"

screen -S midrc_559_combined_dl -X quit >/dev/null 2>&1 || true
pkill -f "/data/tools/gen3-client.*download-multiple" >/dev/null 2>&1 || true

TS=$(date +%Y%m%dT%H%M%S)
LOG="$LOG_DIR/midrc_559_download_restarted_${TS}.log"

echo "RESTART_LOG:$LOG"

screen -dmS midrc_559_combined_dl bash -lc "\
  $BIN download-multiple \
  --profile=midrc \
  --manifest=$MANIFEST \
  --download-path=$DL_ROOT \
  --filename-format=combined \
  --skip-completed \
  --no-prompt \
  --numparallel=2 \
  >> '$LOG' 2>&1"

sleep 2

echo "SCREEN:"
screen -ls 2>/dev/null | grep midrc_559_combined_dl || true

echo "PROC:"
pgrep -af "/data/tools/gen3-client.*download-multiple" || true

echo "FILES_TOTAL:"
find "$DL_ROOT" -type f 2>/dev/null | wc -l

echo "RECENT10:"
find "$DL_ROOT" -type f -mmin -10 2>/dev/null | wc -l

echo "LOG_HEAD:"
head -n 20 "$LOG" || true
