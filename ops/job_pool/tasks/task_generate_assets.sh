#!/usr/bin/env bash
set -euo pipefail
cd /data/JDCNET/src
export PYTHONPATH=/data/JDCNET/src
python3 -m jdcnet_exp.generate_paper_assets
