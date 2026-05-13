#!/usr/bin/env bash
set -euo pipefail

# Locked MIDRC validation for the next "validated architecture" decision.
#
# This script intentionally runs a small, pre-specified matrix:
#   1) CT teacher
#   2) X-ray supervised
#   3) plain CT logit KD
#   4) conservative reliability-gated KD
#
# The candidate is locked to the only robust BIMCV Path-C sweep signal:
# confidence gate threshold=0.55 and projection weight=0.0. Projection losses
# are not enabled unless explicitly overridden in a future, pre-registered run.

REPO=${REPO:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}
RAW_ROOT=${RAW_ROOT:-/root/autodl-tmp/midrc/raw_559cases_combined}
META=${META:-$REPO/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.metadata.json}
OUT=${OUT:-/root/autodl-tmp/midrc/locked_validation}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/midrc_locked_validation}
RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/midrc_locked_validation}
CONFIG_DIR=${CONFIG_DIR:-$REPO/configs/midrc_locked_validation}
PREFIX=${PREFIX:-midrc_locked_validation}
SEEDS=${SEEDS:-42 43 44}
EPOCHS=${EPOCHS:-30}
BATCH_SIZE=${BATCH_SIZE:-16}
INPUT_SIZE=${INPUT_SIZE:-224}
NUM_WORKERS=${NUM_WORKERS:-2}
TRAIN_FRAC=${TRAIN_FRAC:-0.70}
VAL_FRAC=${VAL_FRAC:-0.15}
TEST_FRAC=${TEST_FRAC:-0.15}
MAX_CASES=${MAX_CASES:-}
GATE_THRESHOLD=${GATE_THRESHOLD:-0.55}
GATE_FLOOR=${GATE_FLOOR:-0.00}
GATE_POWER=${GATE_POWER:-1.0}
GATE_REQUIRES_CORRECT=${GATE_REQUIRES_CORRECT:-1}
GATE_MIN_MARGIN=${GATE_MIN_MARGIN:-0.0}
GATE_MAX_ENTROPY=${GATE_MAX_ENTROPY:--1.0}
POSITIVE_GATE_THRESHOLD=${POSITIVE_GATE_THRESHOLD:--1.0}
NEGATIVE_GATE_THRESHOLD=${NEGATIVE_GATE_THRESHOLD:--1.0}
AUTO_SHUTDOWN=${AUTO_SHUTDOWN:-0}
SHUTDOWN_DELAY_SECONDS=${SHUTDOWN_DELAY_SECONDS:-60}

mkdir -p "$OUT" "$LOG_DIR" "$RUN_ROOT" "$CONFIG_DIR"
cd "$REPO"

STATUS="$LOG_DIR/status.tsv"
SUMMARY_CSV="$LOG_DIR/summary.csv"

log() {
  printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"
}

done_run() {
  local run_dir="$1"
  [ -s "$run_dir/history.csv" ] && [ -s "$run_dir/best_metrics.json" ] && [ -s "$run_dir/best.pt" ]
}

maybe_prepare_data() {
  local paired="$OUT/${PREFIX}_paired_manifest.csv"
  local ct="$OUT/${PREFIX}_ct_manifest.csv"
  local summary="$OUT/${PREFIX}_summary.json"
  if [ -s "$paired" ] && [ -s "$ct" ] && [ -s "$summary" ]; then
    log "SKIP prepare_midrc_dataset cached"
    return
  fi

  log "START prepare_midrc_dataset"
  cmd=(
    "$PYTHON_BIN" -u -m jdcnet_exp.prepare_midrc_dataset
    --metadata-json "$META"
    --raw-root "$RAW_ROOT"
    --output-dir "$OUT"
    --prefix "$PREFIX"
    --only-chest
    --negative-multiplier 1.0
    --train-frac "$TRAIN_FRAC"
    --val-frac "$VAL_FRAC"
    --test-frac "$TEST_FRAC"
    --seed 42
  )
  if [ -n "$MAX_CASES" ]; then
    cmd+=(--max-cases "$MAX_CASES")
  fi
  "${cmd[@]}" > "$LOG_DIR/prepare_midrc_dataset.log" 2>&1
  log "DONE prepare_midrc_dataset"
}

write_configs_for_seed() {
  local seed="$1"
  export CONFIG_DIR RUN_ROOT seed EPOCHS BATCH_SIZE INPUT_SIZE NUM_WORKERS OUT PREFIX
  export GATE_THRESHOLD GATE_FLOOR GATE_POWER GATE_REQUIRES_CORRECT
  export GATE_MIN_MARGIN GATE_MAX_ENTROPY POSITIVE_GATE_THRESHOLD NEGATIVE_GATE_THRESHOLD
  "$PYTHON_BIN" - <<'PY'
import json
import os
from copy import deepcopy
from pathlib import Path

config_dir = Path(os.environ["CONFIG_DIR"])
run_root = Path(os.environ["RUN_ROOT"])
seed = int(os.environ["seed"])
epochs = int(os.environ["EPOCHS"])
batch_size = int(os.environ["BATCH_SIZE"])
input_size = int(os.environ["INPUT_SIZE"])
num_workers = int(os.environ["NUM_WORKERS"])
out = Path(os.environ["OUT"])
prefix = os.environ["PREFIX"]
paired_manifest = str(out / f"{prefix}_paired_manifest.csv")
ct_manifest = str(out / f"{prefix}_ct_manifest.csv")

gate_requires_correct = os.environ["GATE_REQUIRES_CORRECT"].lower() not in {"0", "false", "no"}

base_model = {
    "name": "student",
    "num_classes": 2,
    "input_size": input_size,
    "use_dpe": False,
    "use_mhra": False,
    "use_dfpn": False,
    "paired_input": False,
    "backbone": "resnet18",
}
base_data = {
    "train_split": "train",
    "val_split": "val",
    "train_modalities": ["xray"],
    "val_modalities": ["xray"],
    "batch_size": batch_size,
    "num_workers": num_workers,
    "paired_image_column": "teacher_image_path",
    "use_weighted_sampler": True,
}
base_optim = {"epochs": epochs, "learning_rate": 3e-4, "weight_decay": 1e-4}
no_distill = {"enabled": False, "temperature": 4.0, "alpha": 0.6, "teacher_checkpoint": ""}

def write(name: str, payload: dict) -> None:
    (config_dir / f"{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    test_payload = deepcopy(payload)
    test_payload["data"]["val_split"] = "test"
    (config_dir / f"{name}.test.json").write_text(json.dumps(test_payload, indent=2), encoding="utf-8")

teacher_name = f"midrc_locked_teacher_ct_s{seed}"
teacher_run = run_root / teacher_name
teacher = {
    "experiment_name": teacher_name,
    "manifest_path": ct_manifest,
    "output_dir": str(teacher_run),
    "seed": seed,
    "model": {**base_model, "name": "teacher"},
    "data": {**base_data, "train_modalities": ["ct"], "val_modalities": ["ct"]},
    "optimization": base_optim,
    "distillation": no_distill,
}
write(teacher_name, teacher)

supervised_name = f"midrc_locked_xray_supervised_s{seed}"
supervised = {
    "experiment_name": supervised_name,
    "manifest_path": paired_manifest,
    "output_dir": str(run_root / supervised_name),
    "seed": seed,
    "model": base_model,
    "data": base_data,
    "optimization": base_optim,
    "distillation": no_distill,
}
write(supervised_name, supervised)

teacher_checkpoint = str(teacher_run / "best.pt")
plain_name = f"midrc_locked_xray_plain_kd_s{seed}"
plain = deepcopy(supervised)
plain["experiment_name"] = plain_name
plain["output_dir"] = str(run_root / plain_name)
plain["distillation"] = {
    "enabled": True,
    "temperature": 4.0,
    "alpha": 0.6,
    "teacher_checkpoint": teacher_checkpoint,
}
write(plain_name, plain)

gated_name = f"midrc_locked_xray_reliability_gated_kd_s{seed}"
gated = deepcopy(supervised)
gated["experiment_name"] = gated_name
gated["output_dir"] = str(run_root / gated_name)
gated["distillation"] = {
    "enabled": True,
    "temperature": 4.0,
    "alpha": 0.6,
    "teacher_checkpoint": teacher_checkpoint,
    "confidence_gate_enabled": True,
    "confidence_gate_threshold": float(os.environ["GATE_THRESHOLD"]),
    "confidence_gate_positive_threshold": float(os.environ["POSITIVE_GATE_THRESHOLD"]),
    "confidence_gate_negative_threshold": float(os.environ["NEGATIVE_GATE_THRESHOLD"]),
    "confidence_gate_floor": float(os.environ["GATE_FLOOR"]),
    "confidence_gate_power": float(os.environ["GATE_POWER"]),
    "confidence_gate_requires_correct": gate_requires_correct,
    "confidence_gate_min_margin": float(os.environ["GATE_MIN_MARGIN"]),
    "confidence_gate_max_entropy": float(os.environ["GATE_MAX_ENTROPY"]),
    "projected_attention_weight": 0.0,
}
write(gated_name, gated)
PY
}

run_one() {
  local name="$1"
  local run_dir="$RUN_ROOT/$name"
  local config="$CONFIG_DIR/${name}.json"
  if done_run "$run_dir"; then
    log "SKIP $name done"
    return
  fi
  log "START $name"
  "$PYTHON_BIN" -u -m jdcnet_exp.train --config "$config" > "$LOG_DIR/${name}.log" 2>&1
  log "DONE $name"
}

evaluate_test_split() {
  local name="$1"
  local run_dir="$RUN_ROOT/$name"
  local config="$CONFIG_DIR/${name}.test.json"
  local eval_dir="$run_dir/test_eval"
  if [ ! -s "$run_dir/best.pt" ]; then
    log "SKIP_TEST $name missing_checkpoint"
    return
  fi
  if [ -s "$eval_dir/metrics.json" ]; then
    log "SKIP_TEST $name done"
    return
  fi
  log "TEST $name"
  "$PYTHON_BIN" -u -m jdcnet_exp.evaluate \
    --config "$config" \
    --checkpoint "$run_dir/best.pt" \
    --output-dir "$eval_dir" \
    > "$LOG_DIR/${name}.test.log" 2>&1
}

summarize() {
  "$PYTHON_BIN" - <<'PY'
import csv
import json
import os
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
out = Path(os.environ["SUMMARY_CSV"])
rows = []
for run_dir in sorted(run_root.glob("midrc_locked_*")):
    best_path = run_dir / "best_metrics.json"
    test_path = run_dir / "test_eval" / "metrics.json"
    if not best_path.exists():
        continue
    name = run_dir.name
    if "teacher_ct" in name:
        method = "teacher_ct"
    elif "xray_supervised" in name:
        method = "supervised"
    elif "xray_plain_kd" in name:
        method = "plain_kd"
    elif "xray_reliability_gated_kd" in name:
        method = "reliability_gated_kd"
    else:
        method = "unknown"
    seed = int(name.rsplit("_s", 1)[-1])
    val = json.load(open(best_path, encoding="utf-8"))
    test = json.load(open(test_path, encoding="utf-8")) if test_path.exists() else {}
    rows.append({
        "name": name,
        "method": method,
        "seed": seed,
        "val_balanced_accuracy": val.get("balanced_accuracy", ""),
        "val_macro_f1": val.get("macro_f1", ""),
        "val_roc_auc": val.get("roc_auc", ""),
        "test_balanced_accuracy": test.get("balanced_accuracy", ""),
        "test_macro_f1": test.get("macro_f1", ""),
        "test_roc_auc": test.get("roc_auc", ""),
    })

out.parent.mkdir(parents=True, exist_ok=True)
fields = [
    "name", "method", "seed",
    "val_balanced_accuracy", "val_macro_f1", "val_roc_auc",
    "test_balanced_accuracy", "test_macro_f1", "test_roc_auc",
]
with open(out, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {out} rows={len(rows)}")

by_seed = {}
for row in rows:
    by_seed.setdefault(row["seed"], {})[row["method"]] = row
for seed, items in sorted(by_seed.items()):
    gated = items.get("reliability_gated_kd", {}).get("test_balanced_accuracy")
    supervised = items.get("supervised", {}).get("test_balanced_accuracy")
    plain = items.get("plain_kd", {}).get("test_balanced_accuracy")
    if gated not in ("", None) and supervised not in ("", None) and plain not in ("", None):
        gated = float(gated)
        supervised = float(supervised)
        plain = float(plain)
        print(f"seed={seed} gated-supervised={gated-supervised:+.4f} gated-plain={gated-plain:+.4f}")
PY
}

shutdown_after_finish() {
  if [ "$AUTO_SHUTDOWN" != "1" ]; then
    log "AUTO_SHUTDOWN disabled"
    return
  fi
  log "AUTO_SHUTDOWN scheduled delay_seconds=$SHUTDOWN_DELAY_SECONDS"
  sync || true
  nohup bash -lc "sleep '$SHUTDOWN_DELAY_SECONDS'; sync || true; poweroff -f || shutdown -h now || kill -TERM 1 || true" \
    > "$LOG_DIR/auto_shutdown.log" 2>&1 &
}

export RUN_ROOT SUMMARY_CSV
maybe_prepare_data

for seed in $SEEDS; do
  write_configs_for_seed "$seed"
  run_one "midrc_locked_teacher_ct_s${seed}"
  run_one "midrc_locked_xray_supervised_s${seed}"
  run_one "midrc_locked_xray_plain_kd_s${seed}"
  run_one "midrc_locked_xray_reliability_gated_kd_s${seed}"
  evaluate_test_split "midrc_locked_teacher_ct_s${seed}"
  evaluate_test_split "midrc_locked_xray_supervised_s${seed}"
  evaluate_test_split "midrc_locked_xray_plain_kd_s${seed}"
  evaluate_test_split "midrc_locked_xray_reliability_gated_kd_s${seed}"
done

summarize | tee "$LOG_DIR/summary_stdout.txt"
log "DONE locked_validation"
shutdown_after_finish
