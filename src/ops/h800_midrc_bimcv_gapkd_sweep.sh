#!/usr/bin/env bash
set -euo pipefail

# H800 mixed MIDRC+BIMCV GAP-KD sweep focused on seed-43 instability.
# Phase 1: Filter manifest to existing images only
# Phase 2: Train CT teachers (3 seeds)
# Phase 3: Supervised/plain-KD baselines + GAP-KD grid:
#   threshold in {0.55, 0.60, 0.65}
#   projected_attention_weight in {0.00, 0.02, 0.05}
# over seeds {42, 43, 44}.

REPO=${REPO:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}

BIMCV_MANIFEST=${BIMCV_MANIFEST:-/root/autodl-tmp/data/bimcv/bimcv_merged_paired_manifest_pathc.csv}
MIDRC_MANIFEST=${MIDRC_MANIFEST:-$REPO/data/midrc_manifests/generated_559/midrc_559_trainvaltest_manifest.csv}

MIX_OUT_DIR=${MIX_OUT_DIR:-/root/autodl-tmp/mixed/midrc_bimcv_gapkd}
MIX_MANIFEST_RAW=${MIX_MANIFEST_RAW:-$MIX_OUT_DIR/mixed_manifest.csv}
MIX_MANIFEST=${MIX_MANIFEST:-$MIX_OUT_DIR/mixed_manifest_filtered.csv}
MIX_SUMMARY=${MIX_SUMMARY:-$MIX_OUT_DIR/mixed_summary.json}

RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/h800_midrc_bimcv_gapkd}
TEACHER_ROOT=${TEACHER_ROOT:-$RUN_ROOT/teachers}
CONFIG_DIR=${CONFIG_DIR:-$REPO/configs/h800_midrc_bimcv_gapkd}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/h800_midrc_bimcv_gapkd}
SUMMARY_CSV=${SUMMARY_CSV:-$LOG_DIR/summary.csv}

SEEDS=${SEEDS:-"42 43 44"}
THRESHOLDS=${THRESHOLDS:-"0.55 0.60 0.65"}
PROJ_WEIGHTS=${PROJ_WEIGHTS:-"0.00 0.02 0.05"}

# H800 utilization knobs (80GB single card).
INPUT_SIZE=${INPUT_SIZE:-224}
BATCH_SIZE=${BATCH_SIZE:-64}
NUM_WORKERS=${NUM_WORKERS:-12}
EPOCHS=${EPOCHS:-18}
TEACHER_EPOCHS=${TEACHER_EPOCHS:-12}
USE_WEIGHTED_SAMPLER=${USE_WEIGHTED_SAMPLER:-true}

AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-true}
GRAD_ACCUM_STEPS=${GRAD_ACCUM_STEPS:-1}

GPU_ID=${GPU_ID:-0}
AUTO_SHUTDOWN=${AUTO_SHUTDOWN:-0}
SHUTDOWN_DELAY_SECONDS=${SHUTDOWN_DELAY_SECONDS:-30}

mkdir -p "$MIX_OUT_DIR" "$RUN_ROOT" "$TEACHER_ROOT" "$CONFIG_DIR" "$LOG_DIR"
cd "$REPO"

STATUS="$LOG_DIR/status.tsv"
log() {
  printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"
}

done_run() {
  local d="$1"
  [ -s "$d/history.csv" ] && [ -s "$d/best_metrics.json" ] && [ -s "$d/best.pt" ]
}

# ── Phase 0: Generate mixed manifest (if not already done) ──
maybe_prepare_mixed_manifest() {
  if [ -s "$MIX_MANIFEST_RAW" ]; then
    log "SKIP mixed manifest exists: $MIX_MANIFEST_RAW"
    return
  fi

  log "START prepare_mixed_bimcv_midrc_manifest"
  "$PYTHON_BIN" -u -m jdcnet_exp.prepare_mixed_bimcv_midrc_manifest \
    --bimcv-manifest "$BIMCV_MANIFEST" \
    --midrc-manifest "$MIDRC_MANIFEST" \
    --output "$MIX_MANIFEST_RAW" \
    --summary-output "$MIX_SUMMARY" \
    --train-frac 0.7 \
    --val-frac 0.3 \
    --test-frac 0.0 \
    --seed 42 \
    --target-train-positive-ratio 0.5 \
    --target-val-positive-ratio 0.5 \
    --sampling-mode upsample \
    > "$LOG_DIR/prepare_mixed_manifest.log" 2>&1
  log "DONE prepare_mixed_bimcv_midrc_manifest"
}

# ── Phase 1: Filter manifest to only existing images + generate teacher manifest ──
filter_manifest() {
  if [ -s "$MIX_MANIFEST" ]; then
    log "SKIP filtered manifest exists: $MIX_MANIFEST"
    return
  fi
  log "START filter manifest to existing images"
  export MIX_MANIFEST_RAW MIX_MANIFEST MIX_OUT_DIR
  "$PYTHON_BIN" - <<'PYEOF'
import csv, os, json

src_path = os.environ["MIX_MANIFEST_RAW"]
dst_path = os.environ["MIX_MANIFEST"]
mix_dir  = os.environ["MIX_OUT_DIR"]
teacher_path = os.path.join(mix_dir, "teacher_ct_manifest.csv")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

def is_valid_image_path(p):
    """Check path exists, is a file, and has an image extension."""
    if not p or not os.path.isfile(p):
        return False
    return os.path.splitext(p)[1].lower() in IMAGE_EXTS

kept = dropped = 0
with open(src_path) as fin, \
     open(dst_path, "w", newline="") as fout, \
     open(teacher_path, "w", newline="") as fteacher:
    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
    writer.writeheader()
    teacher_fields = list(reader.fieldnames)
    twriter = csv.DictWriter(fteacher, fieldnames=teacher_fields)
    twriter.writeheader()
    for row in reader:
        img = row["image_path"]
        timg = row.get("teacher_image_path", "")
        # Keep only if both student xray and teacher CT images are valid
        if not is_valid_image_path(img):
            dropped += 1
            continue
        if not is_valid_image_path(timg):
            dropped += 1
            continue
        writer.writerow(row)
        kept += 1
        # Teacher manifest: swap image_path with teacher_image_path, modality=ct
        trow = dict(row)
        trow["image_path"] = timg
        trow["modality"] = "ct"
        twriter.writerow(trow)

summary = {"kept": kept, "dropped": dropped, "ratio": round(kept / max(kept + dropped, 1), 3)}
print(json.dumps(summary))
print(f"Teacher manifest: {teacher_path}")
PYEOF
  log "DONE filter manifest: $(wc -l < "$MIX_MANIFEST") rows"
}

write_configs() {
  export CONFIG_DIR RUN_ROOT TEACHER_ROOT MIX_MANIFEST MIX_OUT_DIR INPUT_SIZE BATCH_SIZE NUM_WORKERS EPOCHS TEACHER_EPOCHS \
    USE_WEIGHTED_SAMPLER AMP CHANNELS_LAST TORCH_COMPILE GRAD_ACCUM_STEPS \
    SEEDS THRESHOLDS PROJ_WEIGHTS

  "$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

config_dir = Path(os.environ["CONFIG_DIR"])
run_root = Path(os.environ["RUN_ROOT"])
teacher_root = Path(os.environ["TEACHER_ROOT"])
manifest = os.environ["MIX_MANIFEST"]
input_size = int(os.environ["INPUT_SIZE"])
batch_size = int(os.environ["BATCH_SIZE"])
num_workers = int(os.environ["NUM_WORKERS"])
epochs = int(os.environ["EPOCHS"])
teacher_epochs = int(os.environ["TEACHER_EPOCHS"])
weighted = os.environ["USE_WEIGHTED_SAMPLER"].lower() == "true"
amp = os.environ["AMP"].lower() == "true"
channels_last = os.environ["CHANNELS_LAST"].lower() == "true"
torch_compile = os.environ["TORCH_COMPILE"].lower() == "true"
grad_accum = int(os.environ["GRAD_ACCUM_STEPS"])

seeds = [int(x) for x in os.environ["SEEDS"].split()]
thresholds = [float(x) for x in os.environ["THRESHOLDS"].split()]
proj_weights = [float(x) for x in os.environ["PROJ_WEIGHTS"].split()]

base_student_model = {
    "name": "student",
    "num_classes": 2,
    "input_size": input_size,
    "use_dpe": True,
    "use_mhra": True,
    "use_dfpn": True,
    "paired_input": False,
    "backbone": "resnet18",
}
base_teacher_model = {
    "name": "teacher",
    "num_classes": 2,
    "input_size": input_size,
    "use_dpe": True,
    "use_mhra": True,
    "use_dfpn": True,
    "paired_input": False,
    "backbone": "resnet18",
}
base_student_data = {
    "train_split": "train",
    "val_split": "val",
    "train_modalities": ["xray"],
    "val_modalities": ["xray"],
    "batch_size": batch_size,
    "num_workers": num_workers,
    "paired_image_column": "teacher_image_path",
    "use_weighted_sampler": weighted,
}
base_teacher_data = {
    "train_split": "train",
    "val_split": "val",
    "train_modalities": ["ct"],
    "val_modalities": ["ct"],
    "batch_size": batch_size,
    "num_workers": num_workers,
    "paired_image_column": "teacher_image_path",
    "use_weighted_sampler": weighted,
}
base_optim = {
    "epochs": epochs,
    "learning_rate": 3e-4,
    "weight_decay": 1e-4,
    "grad_accum_steps": grad_accum,
    "amp": amp,
    "channels_last": channels_last,
    "torch_compile": torch_compile,
}
teacher_optim = {**base_optim, "epochs": teacher_epochs}
no_distill = {"enabled": False, "temperature": 4.0, "alpha": 0.6, "teacher_checkpoint": ""}

cfg_count = 0
for seed in seeds:
    teacher_name = f"mix_h800_teacher_ct_s{seed}"
    teacher_ckpt = str(teacher_root / teacher_name / "best.pt")

    # Teacher (CT supervised) — uses teacher_ct_manifest.
    teacher_manifest = str(Path(os.environ["MIX_OUT_DIR"]) / "teacher_ct_manifest.csv")
    teacher_cfg = {
        "experiment_name": teacher_name,
        "manifest_path": teacher_manifest,
        "output_dir": str(teacher_root / teacher_name),
        "seed": seed,
        "model": base_teacher_model,
        "data": base_teacher_data,
        "optimization": teacher_optim,
        "distillation": no_distill,
    }
    (config_dir / f"{teacher_name}.json").write_text(json.dumps(teacher_cfg, indent=2), encoding="utf-8")
    cfg_count += 1

    # Baseline supervised (student xray).
    sup_name = f"mix_h800_supervised_s{seed}"
    sup_cfg = {
        "experiment_name": sup_name,
        "manifest_path": manifest,
        "output_dir": str(run_root / sup_name),
        "seed": seed,
        "model": base_student_model,
        "data": base_student_data,
        "optimization": base_optim,
        "distillation": no_distill,
    }
    (config_dir / f"{sup_name}.json").write_text(json.dumps(sup_cfg, indent=2), encoding="utf-8")
    cfg_count += 1

    # Baseline plain KD.
    plain_name = f"mix_h800_plain_kd_s{seed}"
    plain_cfg = {
        **sup_cfg,
        "experiment_name": plain_name,
        "output_dir": str(run_root / plain_name),
        "distillation": {
            "enabled": True,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": teacher_ckpt,
        },
    }
    (config_dir / f"{plain_name}.json").write_text(json.dumps(plain_cfg, indent=2), encoding="utf-8")
    cfg_count += 1

    # GAP-KD sweep.
    for thr in thresholds:
        thr_tag = f"{int(round(thr * 100)):03d}"
        for proj in proj_weights:
            proj_tag = f"{int(round(proj * 1000)):04d}"
            name = f"mix_h800_gapkd_thr{thr_tag}_proj{proj_tag}_s{seed}"
            cfg = {
                **sup_cfg,
                "experiment_name": name,
                "output_dir": str(run_root / name),
                "distillation": {
                    "enabled": True,
                    "temperature": 4.0,
                    "alpha": 0.6,
                    "teacher_checkpoint": teacher_ckpt,
                    "confidence_gate_enabled": True,
                    "confidence_gate_threshold": float(thr),
                    "confidence_gate_floor": 0.10,
                    "confidence_gate_power": 1.0,
                    "confidence_gate_requires_correct": True,
                    "projected_attention_weight": float(proj),
                },
            }
            (config_dir / f"{name}.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            cfg_count += 1

print(f"wrote {cfg_count} configs to {config_dir}")
PY
}

# ── Phase 2: Train CT teachers ──
train_teachers() {
  local cfg
  for cfg in "$CONFIG_DIR"/mix_h800_teacher_ct_s*.json; do
    local name
    name=$(basename "$cfg" .json)
    local run_dir="$TEACHER_ROOT/$name"
    if done_run "$run_dir"; then
      log "SKIP teacher done $name"
      continue
    fi
    log "START teacher $name"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PYTHON_BIN" -u -m jdcnet_exp.train --config "$cfg" > "$LOG_DIR/${name}.log" 2>&1
    log "DONE teacher $name"
  done
}

# ── Phase 3: Run student experiments ──
run_students() {
  local cfg
  for cfg in "$CONFIG_DIR"/*.json; do
    local name
    name=$(basename "$cfg" .json)
    # Skip teacher configs (already trained).
    case "$name" in mix_h800_teacher_ct_*) continue ;; esac
    local run_dir="$RUN_ROOT/$name"
    if done_run "$run_dir"; then
      log "SKIP done $name"
      continue
    fi
    log "START $name"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PYTHON_BIN" -u -m jdcnet_exp.train --config "$cfg" > "$LOG_DIR/${name}.log" 2>&1
    log "DONE $name"
  done
}

summarize() {
  export RUN_ROOT SUMMARY_CSV
  "$PYTHON_BIN" - <<'PY'
import csv
import json
import os
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
out = Path(os.environ["SUMMARY_CSV"])
rows = []
for p in sorted(run_root.glob("*/best_metrics.json")):
    name = p.parent.name
    parts = name.split("_s")
    seed = int(parts[-1]) if len(parts) > 1 else -1
    if "supervised" in name:
        method = "supervised"
    elif "plain_kd" in name:
        method = "plain_kd"
    elif "gapkd" in name:
        method = "gapkd"
    else:
        method = "other"
    metrics = json.loads(p.read_text(encoding="utf-8"))
    row = {
        "name": name,
        "seed": seed,
        "method": method,
        "balanced_accuracy": metrics.get("balanced_accuracy"),
        "macro_f1": metrics.get("macro_f1"),
        "mcc": metrics.get("mcc"),
    }
    if method == "gapkd":
        thr = ""
        proj = ""
        for token in name.split("_"):
            if token.startswith("thr"):
                thr = token.replace("thr", "")
            if token.startswith("proj"):
                proj = token.replace("proj", "")
        row["thr_tag"] = thr
        row["proj_tag"] = proj
    else:
        row["thr_tag"] = ""
        row["proj_tag"] = ""
    rows.append(row)

out.parent.mkdir(parents=True, exist_ok=True)
fields = ["name", "seed", "method", "thr_tag", "proj_tag", "balanced_accuracy", "macro_f1", "mcc"]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow(r)

print(f"Wrote {out} rows={len(rows)}")

by_seed = {}
for r in rows:
    by_seed.setdefault(r["seed"], {})[r["name"]] = r

for seed in sorted(k for k in by_seed if k >= 0):
    sup = next((x for x in rows if x["seed"] == seed and x["method"] == "supervised"), None)
    plain = next((x for x in rows if x["seed"] == seed and x["method"] == "plain_kd"), None)
    print(f"seed={seed} supervised={sup['balanced_accuracy'] if sup else 'NA'} plain={plain['balanced_accuracy'] if plain else 'NA'}")
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

log "START mixed sweep"
maybe_prepare_mixed_manifest
filter_manifest
write_configs
log "Phase 2: training teachers"
train_teachers
log "Phase 3: student experiments"
run_students
summarize | tee "$LOG_DIR/summary_stdout.txt"
log "DONE mixed sweep"
shutdown_after_finish
