#!/usr/bin/env bash
set -euo pipefail

HOST="${JDCNET_R3090_SSH_TARGET:-${SSH_TARGET:-}}"
if [[ -z "${HOST}" ]]; then
  echo "Set JDCNET_R3090_SSH_TARGET to an SSH host or ~/.ssh/config alias." >&2
  exit 2
fi

SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=8
  -o StrictHostKeyChecking=accept-new
  -o LogLevel=ERROR
)

base=979
i=0
while true; do
  i=$((i+1))
  ts=$(date +"%H:%M:%S")
  cnt=$(ssh "${SSH_OPTIONS[@]}" "$HOST" "find /data1/midrc/raw_559cases_combined -type f 2>/dev/null | wc -l" 2>/dev/null | tr -d ' \r\n')
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
