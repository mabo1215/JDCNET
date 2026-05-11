#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/data/JDCNET/src}
CFG_DIR="$ROOT/configs/bimcv_gapkd_pilot"
RUN_ROOT="$ROOT/runs/bimcv_gapkd_pilot"
LOG_ROOT=${LOG_ROOT:-/data/logs/bimcv_gapkd_pilot}
MANIFEST=${MANIFEST:-data/bimcv/bimcv_merged_paired_manifest_pathc.csv}
TEACHER_CKPT=${TEACHER_CKPT:-/data/JDCNET/src/runs/bimcv_pathc/bimcv_resnet18_pathc_teacher_ct_s42/best.pt}
EPOCHS=${EPOCHS:-50}

mkdir -p "$CFG_DIR" "$RUN_ROOT" "$LOG_ROOT"

if [[ ! -f "$TEACHER_CKPT" ]]; then
  echo "[ERROR] teacher checkpoint missing: $TEACHER_CKPT"
  exit 2
fi

python3 - "$CFG_DIR" "$RUN_ROOT" "$MANIFEST" "$TEACHER_CKPT" "$EPOCHS" <<'PY'
import json
import os
import sys
from pathlib import Path

cfg_dir = Path(sys.argv[1])
run_root = Path(sys.argv[2])
manifest = sys.argv[3]
teacher_ckpt = sys.argv[4]
epochs = int(sys.argv[5])

base = {
    "seed": 42,
    "model": {
        "name": "student",
        "num_classes": 2,
        "input_size": 224,
        "use_dpe": False,
        "use_mhra": False,
        "use_dfpn": False,
        "paired_input": False,
        "backbone": "resnet18",
    },
    "data": {
        "train_split": "train",
        "val_split": "val",
        "train_modalities": ["xray"],
        "val_modalities": ["xray"],
        "batch_size": 16,
        "num_workers": 0,
        "paired_image_column": "teacher_image_path",
        "use_weighted_sampler": True,
    },
    "optimization": {
        "epochs": epochs,
        "learning_rate": 3e-4,
        "weight_decay": 1e-4,
    },
}

experiments = {
    "gapkd_pilot_xray_supervised_s42": {
        "distillation": {
            "enabled": False,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": "",
        }
    },
    "gapkd_pilot_plain_kd_s42": {
        "distillation": {
            "enabled": True,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": teacher_ckpt,
        }
    },
    "gapkd_pilot_gated_kd_s42": {
        "distillation": {
            "enabled": True,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": teacher_ckpt,
            "confidence_gate_enabled": True,
            "confidence_gate_threshold": 0.6,
            "confidence_gate_floor": 0.05,
            "confidence_gate_power": 1.0,
            "confidence_gate_requires_correct": True,
        }
    },
    "gapkd_pilot_gated_projattn_kd_s42": {
        "distillation": {
            "enabled": True,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": teacher_ckpt,
            "confidence_gate_enabled": True,
            "confidence_gate_threshold": 0.6,
            "confidence_gate_floor": 0.05,
            "confidence_gate_power": 1.0,
            "confidence_gate_requires_correct": True,
            "projected_attention_weight": 0.2,
        }
    },
}

for exp, patch in experiments.items():
    payload = dict(base)
    payload["experiment_name"] = exp
    payload["manifest_path"] = manifest
    payload["output_dir"] = f"runs/bimcv_gapkd_pilot/{exp}"
    payload["distillation"] = patch["distillation"]
    out_path = cfg_dir / f"{exp}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(f"wrote {len(experiments)} configs to {cfg_dir}")
PY

configs=(
  "gapkd_pilot_xray_supervised_s42"
  "gapkd_pilot_plain_kd_s42"
  "gapkd_pilot_gated_kd_s42"
  "gapkd_pilot_gated_projattn_kd_s42"
)

gpus=(0 1 2 3)

for i in "${!configs[@]}"; do
  exp="${configs[$i]}"
  gpu="${gpus[$i]}"
  cfg="$CFG_DIR/${exp}.json"
  run_dir="$RUN_ROOT/${exp}"
  log_file="$LOG_ROOT/${exp}.log"
  screen_name="gapkd_pilot_g${gpu}"

  if [[ -s "$run_dir/best_metrics.json" && -s "$run_dir/best.pt" ]]; then
    echo "[SKIP] completed: $exp"
    continue
  fi

  screen -S "$screen_name" -X quit >/dev/null 2>&1 || true
  screen -dmS "$screen_name" bash -lc "cd '$ROOT' && CUDA_VISIBLE_DEVICES=$gpu python3 -m jdcnet_exp.train --config '$cfg' > '$log_file' 2>&1"
  echo "[LAUNCHED] gpu=$gpu exp=$exp screen=$screen_name"
done

echo "[STATUS]"
for i in "${!configs[@]}"; do
  exp="${configs[$i]}"
  gpu="${gpus[$i]}"
  screen_name="gapkd_pilot_g${gpu}"
  echo "- $exp => $screen_name"
done
