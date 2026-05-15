#!/usr/bin/env bash
set -euo pipefail
# Summarize DRR Teacher CV + Extended Seeds + Batch64 experiments

TAG=${TAG:-bimcv_drr_cv_20260515}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
PYTHON_BIN=${PYTHON_BIN:-python3}

"$PYTHON_BIN" - << 'PY'
import json, os, re, math
import numpy as np
from pathlib import Path

run_root = Path(os.environ.get("RUN_ROOT", "/data1/midrc/runs/bimcv_drr_cv_20260515"))
log_dir = Path(os.environ.get("LOG_DIR", "/data1/logs/bimcv_drr_cv_20260515"))

def load_metric(run_dir):
    p = run_dir / "test_eval" / "metrics.json"
    if p.exists():
        return json.loads(p.read_text())
    return None

def bootstrap_ci(deltas, n=10000, ci=0.95):
    if not deltas:
        return float('nan'), float('nan')
    d = np.array(deltas)
    boot = np.random.choice(d, size=(n, len(d)), replace=True).mean(axis=1)
    lo = np.percentile(boot, (1-ci)/2*100)
    hi = np.percentile(boot, (1+ci)/2*100)
    return float(lo), float(hi)

np.random.seed(42)

# ── Collect runs by experiment ────────────────────────────────────────────────
runs = {}
for d in sorted(run_root.iterdir()):
    m = load_metric(d)
    if m is None:
        continue
    name = d.name
    ba = m.get("balanced_accuracy", m.get("val_balanced_accuracy", float('nan')))
    f1 = m.get("macro_f1", m.get("val_macro_f1", float('nan')))
    runs[name] = {"ba": ba, "f1": f1}

def get_tag(name):
    if name.startswith("drr_e1_"): return "exp1"
    if name.startswith("e2_"):     return "exp2"
    if name.startswith("e3_"):     return "exp3"
    return "other"

def get_row(name):
    if "_teacher" in name and "gated" not in name and "plain" not in name and "supervised" not in name:
        return "teacher"
    if "_supervised" in name: return "supervised"
    if "_plain_kd" in name:   return "plain_kd"
    if "_gated_kd" in name:   return "gated_kd"
    return "other"

def get_fold_seed(name):
    fm = re.search(r'_f(\d+)_s(\d+)', name)
    return (int(fm.group(1)), int(fm.group(2))) if fm else (None, None)

# ── Per-experiment analysis ───────────────────────────────────────────────────
report_lines = [f"# DRR Teacher CV Decision Report ({os.environ.get('TAG','bimcv_drr_cv_20260515')})\n"]

rows_parsed = len(runs)
report_lines.append(f"runs parsed: {rows_parsed}\n")

for exp_tag, exp_label in [("exp1", "EXP1: DRR Teacher 5-fold (seeds 42-44)"),
                             ("exp2", "EXP2: Extended Seeds 45-47 (CT mid-slice)"),
                             ("exp3", "EXP3: Batch=64 Sensitivity (seeds 42-44)")]:
    exp_runs = {k: v for k, v in runs.items() if get_tag(k) == exp_tag}
    if not exp_runs:
        report_lines.append(f"\n## {exp_label}\nNo completed runs.\n")
        continue

    # Build (fold, seed) → {row: ba} table
    cells = {}
    for name, vals in exp_runs.items():
        fold, seed = get_fold_seed(name)
        row = get_row(name)
        if fold is None: continue
        key = (fold, seed)
        if key not in cells: cells[key] = {}
        cells[key][row] = vals["ba"]

    # Compute paired deltas
    deltas_gated_sup = []
    deltas_gated_plain = []
    deltas_teacher_sup = []
    method_bas = {"teacher": [], "supervised": [], "plain_kd": [], "gated_kd": []}

    for (fold, seed), row_vals in cells.items():
        for meth, ba_list in method_bas.items():
            if meth in row_vals and not math.isnan(row_vals[meth]):
                ba_list.append(row_vals[meth])
        if "gated_kd" in row_vals and "supervised" in row_vals:
            d = row_vals["gated_kd"] - row_vals["supervised"]
            if not math.isnan(d): deltas_gated_sup.append(d)
        if "gated_kd" in row_vals and "plain_kd" in row_vals:
            d = row_vals["gated_kd"] - row_vals["plain_kd"]
            if not math.isnan(d): deltas_gated_plain.append(d)
        if "teacher" in row_vals and "supervised" in row_vals:
            d = row_vals["teacher"] - row_vals["supervised"]
            if not math.isnan(d): deltas_teacher_sup.append(d)

    report_lines.append(f"\n## {exp_label}\n")
    report_lines.append(f"Completed fold-seed cells: {len(cells)}\n")
    report_lines.append("\n### Method means\n")
    report_lines.append("| Method | n | Mean BA | Mean ± std |\n|---|---|---|---|\n")
    for meth, bas in method_bas.items():
        if bas:
            report_lines.append(f"| {meth} | {len(bas)} | {np.mean(bas):.4f} | {np.std(bas):.4f} |\n")

    report_lines.append("\n### Paired deltas vs supervised\n")
    report_lines.append("| Comparison | n | Mean ΔBA | 95% CI | Pos / Neg |\n|---|---|---|---|---|\n")
    for deltas, label in [(deltas_teacher_sup, "teacher − supervised"),
                           (deltas_gated_sup, "gated KD − supervised"),
                           (deltas_gated_plain, "gated KD − plain KD")]:
        if not deltas:
            continue
        lo, hi = bootstrap_ci(deltas)
        pos = sum(d > 0 for d in deltas)
        neg = sum(d < 0 for d in deltas)
        mean_d = np.mean(deltas)
        validated = "✓ VALIDATED" if mean_d >= 0.03 and lo > 0 else ("≈ NEAR" if mean_d >= 0.03 or lo > -0.01 else "✗ FAIL")
        report_lines.append(
            f"| {label} | {len(deltas)} | {mean_d:+.4f} | [{lo:+.4f}, {hi:+.4f}] | "
            f"{pos}/{neg} | {validated} |\n")

    # For exp2: also combine with exp1 seeds for same T/thr
    if exp_tag == "exp2" and deltas_gated_sup:
        report_lines.append(f"\n### Exp2 gated KD vs supervised: "
                             f"mean={np.mean(deltas_gated_sup):+.4f}, "
                             f"pos={sum(d>0 for d in deltas_gated_sup)}/{len(deltas_gated_sup)}\n")

# ── Combine exp2 seeds 42-47 ──────────────────────────────────────────────────
# collect e2 + original seeds 42-44 for same method (gated_kd T=4 thr=0.50)
report_lines.append("\n## COMBINED: exp2 seeds 45-47 + calibration scan T=4,thr=0.50 (seeds 42-44)\n")
report_lines.append("(Check calibration_scan cell_summary for seeds 42-44 T=4,thr=0.50 data)\n")

report_path = log_dir / "decision_report.md"
report_path.write_text("".join(report_lines))
print(f"wrote report to {report_path}")

# Also write CSV
import csv
summary_rows = []
for name, vals in runs.items():
    fold, seed = get_fold_seed(name)
    summary_rows.append({
        "exp": get_tag(name), "row": get_row(name),
        "fold": fold, "seed": seed, "name": name,
        "ba": vals["ba"], "f1": vals["f1"]
    })

csv_path = log_dir / "run_summary.csv"
if summary_rows:
    with open(str(csv_path), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["exp","row","fold","seed","name","ba","f1"])
        w.writeheader(); w.writerows(summary_rows)
print(f"wrote {len(summary_rows)} rows to {csv_path}")
PY
