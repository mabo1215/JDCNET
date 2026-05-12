#!/usr/bin/env bash
set -euo pipefail

REPO=${REPO:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}
RAW_ROOT=${RAW_ROOT:-/root/autodl-tmp/midrc/raw_559cases_combined}
META=${META:-$REPO/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.metadata.json}
OUT=${OUT:-/root/autodl-tmp/midrc/pilot_balanced_126}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/midrc_pilot}
RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/midrc_pilot}
CONFIG_DIR=${CONFIG_DIR:-$REPO/configs/midrc_pilot}
SEED=${SEED:-42}
EPOCHS=${EPOCHS:-12}
BATCH_SIZE=${BATCH_SIZE:-16}

mkdir -p "$OUT" "$LOG_DIR" "$RUN_ROOT" "$CONFIG_DIR"
cd "$REPO"

log() {
  printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$LOG_DIR/status.tsv"
}

log "START prepare_midrc_dataset"
"$PYTHON_BIN" -u -m jdcnet_exp.prepare_midrc_dataset \
  --metadata-json "$META" \
  --raw-root "$RAW_ROOT" \
  --output-dir "$OUT" \
  --prefix midrc_balanced_pilot \
  --only-chest \
  --negative-multiplier 1.0 \
  --train-frac 0.7 \
  --val-frac 0.3 \
  --test-frac 0.0 \
  --seed "$SEED" \
  > "$LOG_DIR/prepare_midrc_dataset.log" 2>&1
log "DONE prepare_midrc_dataset"

PAIRED_MANIFEST="$OUT/midrc_balanced_pilot_paired_manifest.csv"
CT_MANIFEST="$OUT/midrc_balanced_pilot_ct_manifest.csv"
TEACHER_RUN="$RUN_ROOT/midrc_pilot_resnet18_teacher_ct_s${SEED}"
SUP_RUN="$RUN_ROOT/midrc_pilot_resnet18_xray_supervised_s${SEED}"
PLAIN_KD_RUN="$RUN_ROOT/midrc_pilot_resnet18_xray_plain_kd_s${SEED}"
GAPKD_RUN="$RUN_ROOT/midrc_pilot_resnet18_xray_gapkd_conf_proj_s${SEED}"

export CONFIG_DIR RUN_ROOT SEED EPOCHS BATCH_SIZE PAIRED_MANIFEST CT_MANIFEST TEACHER_RUN SUP_RUN PLAIN_KD_RUN GAPKD_RUN
"$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

config_dir = Path(os.environ["CONFIG_DIR"])
config_dir.mkdir(parents=True, exist_ok=True)
seed = int(os.environ["SEED"])
epochs = int(os.environ["EPOCHS"])
batch_size = int(os.environ["BATCH_SIZE"])

base_model = {
    "name": "student",
    "num_classes": 2,
    "input_size": 128,
    "use_dpe": True,
    "use_mhra": True,
    "use_dfpn": True,
    "paired_input": False,
    "backbone": "resnet18",
}
base_data = {
    "train_split": "train",
    "val_split": "val",
    "train_modalities": ["xray"],
    "val_modalities": ["xray"],
    "batch_size": batch_size,
    "num_workers": 2,
    "paired_image_column": "teacher_image_path",
    "use_weighted_sampler": True,
}
base_optim = {"epochs": epochs, "learning_rate": 3e-4, "weight_decay": 1e-4}
no_distill = {"enabled": False, "temperature": 4.0, "alpha": 0.6, "teacher_checkpoint": ""}

def write(name, payload):
    path = config_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path

teacher_name = f"midrc_pilot_resnet18_teacher_ct_s{seed}"
teacher = {
    "experiment_name": teacher_name,
    "manifest_path": os.environ["CT_MANIFEST"],
    "output_dir": os.environ["TEACHER_RUN"],
    "seed": seed,
    "model": {**base_model, "name": "teacher"},
    "data": {**base_data, "train_modalities": ["ct"], "val_modalities": ["ct"]},
    "optimization": base_optim,
    "distillation": no_distill,
}
write(teacher_name, teacher)

supervised_name = f"midrc_pilot_resnet18_xray_supervised_s{seed}"
supervised = {
    "experiment_name": supervised_name,
    "manifest_path": os.environ["PAIRED_MANIFEST"],
    "output_dir": os.environ["SUP_RUN"],
    "seed": seed,
    "model": base_model,
    "data": base_data,
    "optimization": base_optim,
    "distillation": no_distill,
}
write(supervised_name, supervised)

teacher_checkpoint = str(Path(os.environ["TEACHER_RUN"]) / "best.pt")
plain_name = f"midrc_pilot_resnet18_xray_plain_kd_s{seed}"
plain = {
    **supervised,
    "experiment_name": plain_name,
    "output_dir": os.environ["PLAIN_KD_RUN"],
    "distillation": {
        "enabled": True,
        "temperature": 4.0,
        "alpha": 0.6,
        "teacher_checkpoint": teacher_checkpoint,
    },
}
write(plain_name, plain)

gap_name = f"midrc_pilot_resnet18_xray_gapkd_conf_proj_s{seed}"
gap = {
    **supervised,
    "experiment_name": gap_name,
    "output_dir": os.environ["GAPKD_RUN"],
    "distillation": {
        "enabled": True,
        "temperature": 4.0,
        "alpha": 0.6,
        "teacher_checkpoint": teacher_checkpoint,
        "confidence_gate_enabled": True,
        "confidence_gate_threshold": 0.65,
        "confidence_gate_floor": 0.10,
        "confidence_gate_power": 1.0,
        "confidence_gate_requires_correct": True,
        "projected_attention_weight": 0.05,
    },
}
write(gap_name, gap)
PY

run_one() {
  local name=$1
  local config="$CONFIG_DIR/${name}.json"
  log "START $name"
  "$PYTHON_BIN" -u -m jdcnet_exp.train --config "$config" > "$LOG_DIR/${name}.log" 2>&1
  log "DONE $name"
}

run_one "midrc_pilot_resnet18_teacher_ct_s${SEED}"
run_one "midrc_pilot_resnet18_xray_supervised_s${SEED}"
run_one "midrc_pilot_resnet18_xray_plain_kd_s${SEED}"
run_one "midrc_pilot_resnet18_xray_gapkd_conf_proj_s${SEED}"

log "DONE all"
