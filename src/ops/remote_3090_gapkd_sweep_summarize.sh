#!/usr/bin/env bash
# Summarize GAP-KD parameter sweep results vs baselines
# Run after remote_3090_gapkd_sweep.sh has finished
set -euo pipefail

ROOT=${ROOT:-/data/JDCNET/src}
RUN_ROOT="$ROOT/runs/bimcv_gapkd_sweep"
LOG_ROOT=${LOG_ROOT:-/data/logs/bimcv_gapkd_sweep}
SUMMARY_CSV="$LOG_ROOT/sweep_summary.csv"
MATRIX_OUT="$LOG_ROOT/sweep_matrix.txt"

python3 - <<PY
import json
import csv
import itertools
from pathlib import Path

rr = Path("$RUN_ROOT")
log_root = Path("$LOG_ROOT")
summary_csv = Path("$SUMMARY_CSV")
matrix_out = Path("$MATRIX_OUT")

seeds = [42, 43, 44]
thresholds = [0.55, 0.60, 0.65]
proj_weights = [0.0, 0.02, 0.05]

# Load baselines
baseline_root = Path("/data/JDCNET/src/runs/bimcv_pathc")
baselines = {}
for tag, pat in [("supervised", "xray_supervised"), ("plain_kd", "xray_cross_modal_kd")]:
    baselines[tag] = {}
    for seed in seeds:
        bm = baseline_root / f"bimcv_resnet18_pathc_{pat}_s{seed}" / "best_metrics.json"
        if bm.exists():
            baselines[tag][seed] = json.loads(bm.read_text()).get("balanced_accuracy")

# Load sweep results
rows = []
for seed, thr, proj in itertools.product(seeds, thresholds, proj_weights):
    thr_str = f"{int(thr*100):03d}"
    proj_str = f"{int(proj*1000):04d}"
    name = f"bimcv_sweep_thr{thr_str}_proj{proj_str}_s{seed}"
    bm = rr / name / "best_metrics.json"
    if bm.exists():
        m = json.loads(bm.read_text())
        ba = m.get("balanced_accuracy")
        sup_ba = baselines["supervised"].get(seed)
        plain_ba = baselines["plain_kd"].get(seed)
        rows.append({
            "name": name,
            "seed": seed,
            "threshold": thr,
            "proj_weight": proj,
            "balanced_accuracy": ba,
            "delta_vs_supervised": round(ba - sup_ba, 4) if ba and sup_ba else None,
            "delta_vs_plain_kd": round(ba - plain_ba, 4) if ba and plain_ba else None,
        })
    else:
        rows.append({
            "name": name,
            "seed": seed,
            "threshold": thr,
            "proj_weight": proj,
            "balanced_accuracy": None,
            "delta_vs_supervised": None,
            "delta_vs_plain_kd": None,
        })

# Write CSV
fields = ["name","seed","threshold","proj_weight","balanced_accuracy","delta_vs_supervised","delta_vs_plain_kd"]
with open(summary_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {summary_csv}")

# Print matrix: rows=proj_weight, cols=threshold, per seed
lines = []
lines.append("=== GAP-KD Parameter Sweep — BIMCV pathC (delta BA vs plain_kd) ===")
lines.append("")
for seed in seeds:
    sup_ba = baselines["supervised"].get(seed, "?")
    plain_ba = baselines["plain_kd"].get(seed, "?")
    lines.append(f"Seed {seed}  supervised={sup_ba:.4f}  plain_kd={plain_ba:.4f}" if isinstance(sup_ba, float) else f"Seed {seed}")
    header = "{:>12s}".format("proj_w\\thr") + "".join(f"  thr={t:.2f}" for t in thresholds)
    lines.append(header)
    for proj in proj_weights:
        row_str = f"{'proj='+str(proj):>12s}"
        for thr in thresholds:
            thr_str = f"{int(thr*100):03d}"
            proj_str = f"{int(proj*1000):04d}"
            name = f"bimcv_sweep_thr{thr_str}_proj{proj_str}_s{seed}"
            entry = next((r for r in rows if r["name"] == name), None)
            if entry and entry["delta_vs_plain_kd"] is not None:
                val = f"{entry['delta_vs_plain_kd']:+.4f}"
            elif entry and entry["balanced_accuracy"] is not None:
                val = f" ba={entry['balanced_accuracy']:.4f}"
            else:
                val = "  (pend)"
            row_str += f"  {val:>8s}"
        lines.append(row_str)
    lines.append("")

# Also print all-seed stable combos
lines.append("=== Stable combos (all 3 seeds delta_vs_plain_kd > 0) ===")
for thr, proj in itertools.product(thresholds, proj_weights):
    deltas = []
    for seed in seeds:
        thr_str = f"{int(thr*100):03d}"
        proj_str = f"{int(proj*1000):04d}"
        name = f"bimcv_sweep_thr{thr_str}_proj{proj_str}_s{seed}"
        entry = next((r for r in rows if r["name"] == name), None)
        if entry and entry["delta_vs_plain_kd"] is not None:
            deltas.append(entry["delta_vs_plain_kd"])
    if len(deltas) == 3 and all(d > 0 for d in deltas):
        mean_d = sum(deltas)/3
        lines.append(f"  thr={thr:.2f} proj={proj:.3f}  deltas={[round(x,4) for x in deltas]}  mean={mean_d:+.4f}")

matrix_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(matrix_out.read_text())
PY
