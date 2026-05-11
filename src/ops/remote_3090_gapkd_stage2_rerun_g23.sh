#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/data/JDCNET/src}
CFG_DIR="$ROOT/configs/bimcv_gapkd_pilot"
RERUN_CFG_DIR="$ROOT/configs/bimcv_gapkd_pilot_rerun_g23"
RERUN_RUN_ROOT="$ROOT/runs/bimcv_gapkd_pilot_rerun_g23"
LOG_ROOT=${LOG_ROOT:-/data/logs/bimcv_gapkd_pilot_rerun_g23}
CHECK_INTERVAL=${CHECK_INTERVAL:-300}

mkdir -p "$RERUN_CFG_DIR" "$RERUN_RUN_ROOT" "$LOG_ROOT"

echo "[WAIT] waiting for stage-1 GPU2/3 pilot processes to finish..."
while true; do
  if ! pgrep -af "jdcnet_exp.train.*gapkd_pilot_gated_kd_s42.json" >/dev/null \
    && ! pgrep -af "jdcnet_exp.train.*gapkd_pilot_gated_projattn_kd_s42.json" >/dev/null; then
    break
  fi
  date -Is
  echo "  gated_kd_running=$(pgrep -af \"jdcnet_exp.train.*gapkd_pilot_gated_kd_s42.json\" >/dev/null && echo yes || echo no)"
  echo "  gated_proj_running=$(pgrep -af \"jdcnet_exp.train.*gapkd_pilot_gated_projattn_kd_s42.json\" >/dev/null && echo yes || echo no)"
  sleep "$CHECK_INTERVAL"
done

echo "[READY] GPU2/3 jobs finished, preparing rerun configs for first two experiments"

python3 - "$CFG_DIR" "$RERUN_CFG_DIR" <<'PY'
import json
import sys
from pathlib import Path

src_dir = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

mapping = {
    "gapkd_pilot_xray_supervised_s42.json": "gapkd_pilot_xray_supervised_s42_rerun_g2.json",
    "gapkd_pilot_plain_kd_s42.json": "gapkd_pilot_plain_kd_s42_rerun_g3.json",
}

for src_name, out_name in mapping.items():
    payload = json.loads((src_dir / src_name).read_text(encoding='utf-8'))
    exp = payload["experiment_name"] + "_rerun_g23"
    payload["experiment_name"] = exp
    payload["output_dir"] = f"runs/bimcv_gapkd_pilot_rerun_g23/{exp}"
    (out_dir / out_name).write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f"wrote {(out_dir / out_name)}")
PY

screen -S gapkd_rerun_g2 -X quit >/dev/null 2>&1 || true
screen -S gapkd_rerun_g3 -X quit >/dev/null 2>&1 || true

screen -dmS gapkd_rerun_g2 bash -lc "cd '$ROOT' && CUDA_VISIBLE_DEVICES=2 python3 -m jdcnet_exp.train --config '$RERUN_CFG_DIR/gapkd_pilot_xray_supervised_s42_rerun_g2.json' > '$LOG_ROOT/gapkd_pilot_xray_supervised_s42_rerun_g2.log' 2>&1"
screen -dmS gapkd_rerun_g3 bash -lc "cd '$ROOT' && CUDA_VISIBLE_DEVICES=3 python3 -m jdcnet_exp.train --config '$RERUN_CFG_DIR/gapkd_pilot_plain_kd_s42_rerun_g3.json' > '$LOG_ROOT/gapkd_pilot_plain_kd_s42_rerun_g3.log' 2>&1"

echo "[LAUNCHED] rerun on GPU2/3"
echo "  screen: gapkd_rerun_g2"
echo "  screen: gapkd_rerun_g3"
