#!/usr/bin/env bash
set -euo pipefail

# Summarize the BIMCV-only calibration scan (Priority 2).
# Reads:
#   $RUN_ROOT   - calibration scan run directory tree
#   $BASE_ROOT  - prior BIMCV-only 5-fold CV run tree (for xray_supervised baseline)
# Writes:
#   $LOG_DIR/summary_by_run.csv
#   $LOG_DIR/cell_summary.csv
#   $LOG_DIR/decision_report.md

SCAN_TAG=${SCAN_TAG:-bimcv_only_calibration_scan_20260514}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${SCAN_TAG}}
BASE_ROOT=${BASE_ROOT:-/data1/midrc/runs/bimcv_only_5fold_cv_balanced}
LOG_DIR=${LOG_DIR:-/data1/logs/${SCAN_TAG}}
OUT=${OUT:-$LOG_DIR/summary_by_run.csv}
CELL_OUT=${CELL_OUT:-$LOG_DIR/cell_summary.csv}
REPORT=${REPORT:-$LOG_DIR/decision_report.md}
PYTHON_BIN=${PYTHON_BIN:-python3}

mkdir -p "$LOG_DIR"

"$PYTHON_BIN" - "$RUN_ROOT" "$BASE_ROOT" "$OUT" "$CELL_OUT" "$REPORT" <<'PY'
import csv
import json
import random
import re
import statistics
import sys
from pathlib import Path

run_root = Path(sys.argv[1])
base_root = Path(sys.argv[2])
out = Path(sys.argv[3])
cell_out = Path(sys.argv[4])
report = Path(sys.argv[5])

scan_pat = re.compile(
    r"calib_f(?P<fold>\d+)_s(?P<seed>\d+)_gated_kd_t(?P<t>\d+)_thr(?P<thr>\d+)_proj0000"
)
base_pat = re.compile(r"bimcv_only_f(?P<fold>\d+)_s(?P<seed>\d+)_xray_supervised")


def load_metrics(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def last_history_row(run_dir: Path) -> dict:
    hist_path = run_dir / "history.csv"
    if not hist_path.exists():
        return {}
    with open(hist_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1] if rows else {}


supervised: dict[tuple[int, int], float] = {}
for metrics_path in sorted(base_root.glob("*/test_eval/metrics.json")):
    name = metrics_path.parent.parent.name
    m = base_pat.match(name)
    if not m:
        continue
    metrics = load_metrics(metrics_path)
    if not metrics or "balanced_accuracy" not in metrics:
        continue
    supervised[(int(m.group("fold")), int(m.group("seed")))] = float(metrics["balanced_accuracy"])

rows = []
for metrics_path in sorted(run_root.glob("*/test_eval/metrics.json")):
    name = metrics_path.parent.parent.name
    m = scan_pat.match(name)
    if not m:
        continue
    metrics = load_metrics(metrics_path)
    if not metrics or "balanced_accuracy" not in metrics:
        continue
    fold = int(m.group("fold"))
    seed = int(m.group("seed"))
    t = int(m.group("t")) / 10.0
    thr = int(m.group("thr")) / 100.0
    run_dir = metrics_path.parent.parent
    hist = last_history_row(run_dir)
    base_ba = supervised.get((fold, seed))
    ba = float(metrics["balanced_accuracy"])
    delta = ba - base_ba if base_ba is not None else None
    rows.append({
        "name": name,
        "fold": fold,
        "seed": seed,
        "temperature": t,
        "gate_threshold": thr,
        "balanced_accuracy": ba,
        "supervised_ba": base_ba if base_ba is not None else "",
        "delta_vs_supervised_ba": delta if delta is not None else "",
        "macro_f1": metrics.get("macro_f1", ""),
        "specificity": metrics.get("specificity", ""),
        "recall": metrics.get("recall", ""),
        "mcc": metrics.get("mcc", ""),
        "roc_auc": metrics.get("roc_auc", ""),
        "kd_gate_active_fraction_last": hist.get("kd_gate_active_fraction", ""),
        "kd_gate_mean_weight_last": hist.get("kd_gate_mean_weight", ""),
        "teacher_train_accuracy_last": hist.get("teacher_train_accuracy", ""),
        "teacher_train_mean_confidence_last": hist.get("teacher_train_mean_confidence", ""),
    })

fields = [
    "name", "fold", "seed", "temperature", "gate_threshold",
    "balanced_accuracy", "supervised_ba", "delta_vs_supervised_ba",
    "macro_f1", "specificity", "recall", "mcc", "roc_auc",
    "kd_gate_active_fraction_last", "kd_gate_mean_weight_last",
    "teacher_train_accuracy_last", "teacher_train_mean_confidence_last",
]
with open(out, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)


def bootstrap_ci(values: list[float], iters: int = 2000, seed: int = 0) -> tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iters):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters) - 1]
    return (lo, hi)


cells: dict[tuple[float, float], list[dict]] = {}
for r in rows:
    cells.setdefault((r["temperature"], r["gate_threshold"]), []).append(r)

cell_rows = []
for (t, thr), members in sorted(cells.items()):
    bas = [m["balanced_accuracy"] for m in members]
    deltas = [m["delta_vs_supervised_ba"] for m in members if isinstance(m["delta_vs_supervised_ba"], float)]
    gate_active = [float(m["kd_gate_active_fraction_last"]) for m in members
                   if m["kd_gate_active_fraction_last"] not in ("", None)]
    n_pos = sum(1 for d in deltas if d > 0)
    n_zero = sum(1 for d in deltas if d == 0)
    n_neg = sum(1 for d in deltas if d < 0)
    mean_delta = statistics.fmean(deltas) if deltas else float("nan")
    ci_lo, ci_hi = bootstrap_ci(deltas) if deltas else (float("nan"), float("nan"))
    cell_rows.append({
        "temperature": t,
        "gate_threshold": thr,
        "n_runs": len(members),
        "mean_ba": statistics.fmean(bas) if bas else float("nan"),
        "mean_delta_vs_sup": mean_delta,
        "ci95_lo": ci_lo,
        "ci95_hi": ci_hi,
        "pos_runs": n_pos,
        "zero_runs": n_zero,
        "neg_runs": n_neg,
        "mean_gate_active_fraction": statistics.fmean(gate_active) if gate_active else float("nan"),
    })

cell_fields = [
    "temperature", "gate_threshold", "n_runs", "mean_ba", "mean_delta_vs_sup",
    "ci95_lo", "ci95_hi", "pos_runs", "zero_runs", "neg_runs", "mean_gate_active_fraction",
]
with open(cell_out, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=cell_fields)
    writer.writeheader()
    writer.writerows(cell_rows)

lines = ["# BIMCV-only Calibration Scan Decision Report", ""]
lines.append(f"runs parsed: {len(rows)}; cells: {len(cell_rows)}")
lines.append("")
lines.append("| T | thr | n | mean BA | mean ΔBA vs sup | 95% CI | pos/zero/neg | gate active frac |")
lines.append("|---|---|---|---|---|---|---|---|")
for c in cell_rows:
    lines.append(
        f"| {c['temperature']:.1f} | {c['gate_threshold']:.2f} | {c['n_runs']} | "
        f"{c['mean_ba']:.4f} | {c['mean_delta_vs_sup']:+.4f} | "
        f"[{c['ci95_lo']:+.4f}, {c['ci95_hi']:+.4f}] | "
        f"{c['pos_runs']}/{c['zero_runs']}/{c['neg_runs']} | "
        f"{c['mean_gate_active_fraction']:.3f} |"
    )
lines.append("")
winners = [c for c in cell_rows if c["ci95_lo"] > 0 and c["mean_delta_vs_sup"] >= 0.03]
lines.append("## Validated cells (ΔBA mean ≥ +0.03 AND CI lower > 0)")
if winners:
    for c in winners:
        lines.append(
            f"- T={c['temperature']:.1f}, thr={c['gate_threshold']:.2f}: "
            f"ΔBA={c['mean_delta_vs_sup']:+.4f}, "
            f"CI=[{c['ci95_lo']:+.4f}, {c['ci95_hi']:+.4f}]"
        )
else:
    lines.append("- none")

report.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} runs to {out}")
print(f"wrote {len(cell_rows)} cells to {cell_out}")
print(f"wrote report to {report}")
PY
