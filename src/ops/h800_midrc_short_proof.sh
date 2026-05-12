#!/usr/bin/env bash
set -euo pipefail

REPO=${REPO:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}
RAW_ROOT=${RAW_ROOT:-/root/autodl-tmp/midrc/raw_559cases_combined}
META=${META:-$REPO/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.metadata.json}
OUT=${OUT:-/root/autodl-tmp/midrc/pilot_balanced_126}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/midrc_short_proof}
RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/midrc_short_proof}
CONFIG_DIR=${CONFIG_DIR:-$REPO/configs/midrc_short_proof}
SEEDS=${SEEDS:-42 43 44}
EPOCHS=${EPOCHS:-12}
BATCH_SIZE=${BATCH_SIZE:-16}
AUTO_SHUTDOWN=${AUTO_SHUTDOWN:-1}
SHUTDOWN_DELAY_SECONDS=${SHUTDOWN_DELAY_SECONDS:-30}

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
  local paired="$OUT/midrc_balanced_pilot_paired_manifest.csv"
  local ct="$OUT/midrc_balanced_pilot_ct_manifest.csv"
  if [ -s "$paired" ] && [ -s "$ct" ]; then
    log "SKIP prepare_midrc_dataset cached"
    return
  fi
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
    --seed 42 \
    > "$LOG_DIR/prepare_midrc_dataset.log" 2>&1
  log "DONE prepare_midrc_dataset"
}

write_configs_for_seed() {
  local seed="$1"
  export CONFIG_DIR RUN_ROOT seed EPOCHS BATCH_SIZE OUT
  "$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

config_dir = Path(os.environ["CONFIG_DIR"])
run_root = Path(os.environ["RUN_ROOT"])
seed = int(os.environ["seed"])
epochs = int(os.environ["EPOCHS"])
batch_size = int(os.environ["BATCH_SIZE"])
out = Path(os.environ["OUT"])
paired_manifest = str(out / "midrc_balanced_pilot_paired_manifest.csv")
ct_manifest = str(out / "midrc_balanced_pilot_ct_manifest.csv")

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

teacher_name = f"midrc_short_resnet18_teacher_ct_s{seed}"
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

supervised_name = f"midrc_short_resnet18_xray_supervised_s{seed}"
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
plain_name = f"midrc_short_resnet18_xray_plain_kd_s{seed}"
plain = {
    **supervised,
    "experiment_name": plain_name,
    "output_dir": str(run_root / plain_name),
    "distillation": {
        "enabled": True,
        "temperature": 4.0,
        "alpha": 0.6,
        "teacher_checkpoint": teacher_checkpoint,
    },
}
write(plain_name, plain)

gap_name = f"midrc_short_resnet18_xray_gapkd_conf_proj_s{seed}"
gap = {
    **supervised,
    "experiment_name": gap_name,
    "output_dir": str(run_root / gap_name),
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

summarize() {
  "$PYTHON_BIN" - <<'PY'
import csv
import json
import os
from pathlib import Path

run_root = Path(os.environ.get("RUN_ROOT", "/root/autodl-tmp/runs/midrc_short_proof"))
out = Path(os.environ.get("SUMMARY_CSV", "/root/autodl-tmp/logs/midrc_short_proof/summary.csv"))
rows = []
for path in sorted(run_root.glob("*/best_metrics.json")):
    name = path.parent.name
    if "teacher_ct" in name:
        method = "teacher_ct"
    elif "xray_supervised" in name:
        method = "supervised"
    elif "xray_plain_kd" in name:
        method = "plain_kd"
    elif "xray_gapkd_conf_proj" in name:
        method = "gapkd_conf_proj"
    else:
        method = "unknown"
    seed = int(name.rsplit("_s", 1)[-1])
    metrics = json.load(open(path, encoding="utf-8"))
    rows.append({"name": name, "method": method, "seed": seed, **metrics})
out.parent.mkdir(parents=True, exist_ok=True)
fields = ["name", "method", "seed", "balanced_accuracy", "macro_f1", "roc_auc", "pr_auc", "recall", "specificity", "mcc", "accuracy"]
with open(out, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
print(f"Wrote {out} rows={len(rows)}")
by_seed = {}
for row in rows:
    by_seed.setdefault(row["seed"], {})[row["method"]] = row
for seed, items in sorted(by_seed.items()):
    sup = items.get("supervised", {}).get("balanced_accuracy")
    plain = items.get("plain_kd", {}).get("balanced_accuracy")
    gap = items.get("gapkd_conf_proj", {}).get("balanced_accuracy")
    if gap is not None and sup is not None and plain is not None:
        print(f"seed={seed} gap-supervised={gap-sup:+.4f} gap-plain={gap-plain:+.4f}")
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
  run_one "midrc_short_resnet18_teacher_ct_s${seed}"
  run_one "midrc_short_resnet18_xray_supervised_s${seed}"
  run_one "midrc_short_resnet18_xray_plain_kd_s${seed}"
  run_one "midrc_short_resnet18_xray_gapkd_conf_proj_s${seed}"
done

summarize | tee "$LOG_DIR/summary_stdout.txt"
log "DONE all_short_proof"
shutdown_after_finish
