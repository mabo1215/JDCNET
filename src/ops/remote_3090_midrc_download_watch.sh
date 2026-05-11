#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/data1/midrc/raw_559cases_combined}
LOG=${LOG:-/data1/logs/midrc/midrc_559_download_combined.log}
OUT=${OUT:-/data1/logs/midrc/midrc_559_progress.tsv}
INTERVAL=${INTERVAL:-300}

mkdir -p "$(dirname "$OUT")"

if [[ ! -f "$OUT" ]]; then
  echo -e "time\tfiles\tzips\tsize\trecent_failures\trecent_retries" > "$OUT"
fi

while true; do
  now=$(date -Is)
  files=$(find "$ROOT" -type f 2>/dev/null | wc -l | tr -d ' ')
  zips=$(find "$ROOT" -type f -name '*.zip' 2>/dev/null | wc -l | tr -d ' ')
  size=$(du -sh "$ROOT" 2>/dev/null | awk '{print $1}')
  if [[ -z "$size" ]]; then
    size="0"
  fi

  if [[ -f "$LOG" ]]; then
    recent=$(tail -n 2000 "$LOG" || true)
    recent_failures=$(printf "%s" "$recent" | grep -Eic 'error|failed|timeout|connection reset|refused' || true)
    recent_retries=$(printf "%s" "$recent" | grep -Eic 'retry|retries|try again' || true)
  else
    recent_failures=0
    recent_retries=0
  fi

  echo -e "${now}\t${files}\t${zips}\t${size}\t${recent_failures}\t${recent_retries}" >> "$OUT"
  sleep "$INTERVAL"
done
