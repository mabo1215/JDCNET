#!/usr/bin/env bash
set -euo pipefail

# Parallel H800 sweep: run up to N experiments concurrently.
# Each experiment uses ~1.7GB; with 80GB we can safely run 20+ in parallel.

REPO=${REPO:-/root/autodl-tmp/JDCNET/src}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}
CONFIG_DIR=${CONFIG_DIR:-$REPO/configs/h800_midrc_bimcv_gapkd}
RUN_ROOT=${RUN_ROOT:-/root/autodl-tmp/runs/h800_midrc_bimcv_gapkd}
TEACHER_ROOT=${TEACHER_ROOT:-$RUN_ROOT/teachers}
LOG_DIR=${LOG_DIR:-/root/autodl-tmp/logs/h800_midrc_bimcv_gapkd}
SUMMARY_CSV=${SUMMARY_CSV:-$LOG_DIR/summary.csv}
GPU_ID=${GPU_ID:-0}
MAX_PARALLEL=${MAX_PARALLEL:-20}

STATUS="$LOG_DIR/status_parallel.tsv"
log() {
  printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"
}

done_run() {
  local d="$1"
  [ -s "$d/history.csv" ] && [ -s "$d/best_metrics.json" ] && [ -s "$d/best.pt" ]
}

cd "$REPO"

# Collect remaining (non-teacher, not-done) configs.
declare -a pending=()
for cfg in "$CONFIG_DIR"/*.json; do
  name=$(basename "$cfg" .json)
  case "$name" in mix_h800_teacher_ct_*) continue ;; esac
  run_dir="$RUN_ROOT/$name"
  if done_run "$run_dir"; then
    log "SKIP done $name"
    continue
  fi
  pending+=("$cfg")
done

total=${#pending[@]}
log "PARALLEL SWEEP: $total pending configs, max_parallel=$MAX_PARALLEL"

if [ "$total" -eq 0 ]; then
  log "Nothing to run"
  exit 0
fi

# Launch in batches of MAX_PARALLEL.
declare -a pids=()
declare -a names=()
running=0
finished=0

launch_one() {
  local cfg="$1"
  local name
  name=$(basename "$cfg" .json)
  log "LAUNCH $name"
  CUDA_VISIBLE_DEVICES="$GPU_ID" "$PYTHON_BIN" -u -m jdcnet_exp.train \
    --config "$cfg" > "$LOG_DIR/${name}.log" 2>&1 &
  pids+=($!)
  names+=("$name")
  running=$((running + 1))
}

wait_for_slot() {
  # Wait until at least one slot is free.
  while [ "$running" -ge "$MAX_PARALLEL" ]; do
    for i in "${!pids[@]}"; do
      if ! kill -0 "${pids[$i]}" 2>/dev/null; then
        wait "${pids[$i]}" 2>/dev/null || true
        log "DONE ${names[$i]} (exit=$?)"
        unset 'pids[i]'
        unset 'names[i]'
        running=$((running - 1))
        finished=$((finished + 1))
        log "PROGRESS $finished/$total done, $running running"
        # Re-index arrays.
        pids=("${pids[@]}")
        names=("${names[@]}")
        return
      fi
    done
    sleep 2
  done
}

for cfg in "${pending[@]}"; do
  wait_for_slot
  launch_one "$cfg"
done

# Wait for all remaining.
log "All launched, waiting for $running remaining..."
for pid in "${pids[@]}"; do
  wait "$pid" 2>/dev/null || true
done
finished=$total
log "ALL DONE: $finished/$total configs complete"

# Summarize.
export RUN_ROOT SUMMARY_CSV
"$PYTHON_BIN" - <<'PY'
import csv, json, os
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
    thr = proj = ""
    for token in name.split("_"):
        if token.startswith("thr"): thr = token.replace("thr", "")
        if token.startswith("proj"): proj = token.replace("proj", "")
    row["thr_tag"] = thr
    row["proj_tag"] = proj
    rows.append(row)

out.parent.mkdir(parents=True, exist_ok=True)
fields = ["name", "seed", "method", "thr_tag", "proj_tag", "balanced_accuracy", "macro_f1", "mcc"]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(f"Summary: {out} ({len(rows)} rows)")
for r in sorted(rows, key=lambda x: -(x.get("balanced_accuracy") or 0))[:5]:
    print(f"  {r['name']}: bal_acc={r['balanced_accuracy']:.4f} f1={r['macro_f1']:.4f} mcc={r['mcc']:.4f}")
PY
