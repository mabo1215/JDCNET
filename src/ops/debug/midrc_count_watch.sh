#!/usr/bin/env bash
set -u
base=979
i=0
while true; do
  i=$((i+1))
  ts=$(date +"%H:%M:%S")
  cnt=$(sshpass -p mabo1215 ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR mabo1215@10.147.20.176 "find /data1/midrc/raw_559cases_combined -type f 2>/dev/null | wc -l" 2>/dev/null | tr -d ' \r\n')
  if [ -z "$cnt" ]; then
    echo "$ts [round $i] count=NA (ssh/check failed)"
  else
    echo "$ts [round $i] count=$cnt"
    if [ "$cnt" -gt "$base" ]; then
      echo "$ts [SUCCESS] count grew from $base to $cnt"
      break
    fi
  fi
  sleep 60
done
