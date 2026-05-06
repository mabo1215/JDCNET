#!/usr/bin/env bash
set -euo pipefail
cd /data/JDCNET/src
export PYTHONPATH=/data/JDCNET/src
python3 -m jdcnet_exp.summarize_runs --runs-root runs --output runs/summary_after_main.csv
