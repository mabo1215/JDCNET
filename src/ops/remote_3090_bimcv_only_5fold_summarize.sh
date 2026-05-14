#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/bimcv_only_5fold_cv_balanced}
LOG_DIR=${LOG_DIR:-/data1/logs/bimcv_only_5fold_cv_3090_balanced}
OUT=${OUT:-$LOG_DIR/summary_by_run.csv}
REPORT=${REPORT:-$LOG_DIR/decision_report.md}
PYTHON_BIN=${PYTHON_BIN:-python3}

mkdir -p "$LOG_DIR"

"$PYTHON_BIN" - "$RUN_ROOT" "$OUT" "$REPORT" <<'PY'
import csv
import json
import re
import statistics
import sys
from pathlib import Path

run_root = Path(sys.argv[1])
out = Path(sys.argv[2])
report = Path(sys.argv[3])

pattern = re.compile(r"bimcv_only_f(?P<fold>\d+)_s(?P<seed>\d+)_(?P<tail>.+)")
rows = []
for metrics_path in sorted(run_root.glob("*/test_eval/metrics.json")):
    name = metrics_path.parent.parent.name
    match = pattern.match(name)
    if not match:
        continue
    tail = match.group("tail")
    if tail == "teacher_drr":
        method = "teacher_drr"
    elif tail == "xray_supervised":
        method = "xray_supervised"
    elif tail == "plain_kd":
        method = "plain_kd"
    elif tail.startswith("gated_kd"):
        method = "gated_kd"
    else:
        method = tail
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    matrix = metrics.get("confusion_matrix", [[0, 0], [0, 0]])
    n_neg = int(sum(matrix[0])) if len(matrix) > 0 else 0
    n_pos = int(sum(matrix[1])) if len(matrix) > 1 else 0
    history_path = metrics_path.parent.parent / "history.csv"
    gate_active = ""
    gate_weight = ""
    teacher_train_acc = ""
    teacher_train_conf = ""
    if history_path.exists():
        with open(history_path, newline="", encoding="utf-8") as handle:
            hist = list(csv.DictReader(handle))
        if hist:
            last = hist[-1]
            gate_active = last.get("kd_gate_active_fraction", "")
            gate_weight = last.get("kd_gate_mean_weight", "")
            teacher_train_acc = last.get("teacher_train_accuracy", "")
            teacher_train_conf = last.get("teacher_train_mean_confidence", "")
    rows.append({
        "name": name,
        "fold": int(match.group("fold")),
        "seed": int(match.group("seed")),
        "method": method,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "balanced_accuracy": metrics.get("balanced_accuracy"),
        "macro_f1": metrics.get("macro_f1"),
        "specificity": metrics.get("specificity"),
        "recall": metrics.get("recall"),
        "mcc": metrics.get("mcc"),
        "roc_auc": metrics.get("roc_auc"),
        "kd_gate_active_fraction_last": gate_active,
        "kd_gate_mean_weight_last": gate_weight,
        "teacher_train_accuracy_last": teacher_train_acc,
        "teacher_train_mean_confidence_last": teacher_train_conf,
    })

fields = [
    "name", "fold", "seed", "method", "n_pos", "n_neg",
    "balanced_accuracy", "macro_f1", "specificity", "recall", "mcc", "roc_auc",
    "kd_gate_active_fraction_last", "kd_gate_mean_weight_last",
    "teacher_train_accuracy_last", "teacher_train_mean_confidence_last",
]
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

by_key = {}
for row in rows:
    by_key.setdefault((row["fold"], row["seed"]), {})[row["method"]] = row

deltas = []
for key, group in sorted(by_key.items()):
    if {"xray_supervised", "plain_kd", "gated_kd"} <= set(group):
        gated = float(group["gated_kd"]["balanced_accuracy"])
        sup = float(group["xray_supervised"]["balanced_accuracy"])
        plain = float(group["plain_kd"]["balanced_accuracy"])
        deltas.append({
            "fold": key[0],
            "seed": key[1],
            "delta_gated_vs_supervised_ba": gated - sup,
            "delta_gated_vs_plain_ba": gated - plain,
        })

delta_path = out.parent / "delta_summary.csv"
with open(delta_path, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["fold", "seed", "delta_gated_vs_supervised_ba", "delta_gated_vs_plain_ba"])
    writer.writeheader()
    writer.writerows(deltas)

def mean(values):
    return statistics.mean(values) if values else None

def positive_count(values):
    return sum(1 for value in values if value > 0)

delta_sup = [x["delta_gated_vs_supervised_ba"] for x in deltas]
delta_plain = [x["delta_gated_vs_plain_ba"] for x in deltas]
teacher_wins = 0
teacher_pairs = 0
for group in by_key.values():
    if "teacher_drr" in group and "xray_supervised" in group:
        teacher_pairs += 1
        teacher_wins += float(group["teacher_drr"]["balanced_accuracy"]) > float(group["xray_supervised"]["balanced_accuracy"])

lines = [
    "# BIMCV-only 5-fold CV decision report",
    "",
    f"Run root: `{run_root}`",
    f"Rows summarized: {len(rows)}",
    f"Complete fold/seed delta pairs: {len(deltas)}",
    "",
    "## Delta BA summary",
    "",
    f"- mean gated - supervised BA: {mean(delta_sup)}",
    f"- positive gated - supervised pairs: {positive_count(delta_sup)}/{len(delta_sup)}",
    f"- mean gated - plain KD BA: {mean(delta_plain)}",
    f"- positive gated - plain KD pairs: {positive_count(delta_plain)}/{len(delta_plain)}",
    f"- teacher DRR beats supervised pairs: {teacher_wins}/{teacher_pairs}",
    "",
    "## Files",
    "",
    f"- summary_by_run: `{out}`",
    f"- delta_summary: `{delta_path}`",
]
report.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print(f"Wrote {out} rows={len(rows)}")
print(f"Wrote {delta_path} rows={len(deltas)}")
print(f"Wrote {report}")
print("\\n".join(lines))
PY

