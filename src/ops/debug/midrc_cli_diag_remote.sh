#!/usr/bin/env bash
set -euo pipefail

echo "HOST:$(hostname)"
echo "PWD:$(pwd)"

for p in /data /data1 /data/tools/gen3-client /data/secure/midrc /data1/midrc/raw_559cases_combined; do
  if [[ -e "$p" ]]; then
    echo "EXISTS:$p"
  else
    echo "MISSING:$p"
  fi
done

if [[ -x /data/tools/gen3-client ]]; then
  /data/tools/gen3-client --version || true
  /data/tools/gen3-client help download-multiple || true
fi
