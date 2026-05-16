#!/usr/bin/env bash
set -euo pipefail
# Summarize Stage A: BIMCV 510-patient extended paired CV (4 teachers x 4 methods x 5 folds x 3 seeds)

TAG=${TAG:-bimcv_full_paired_cv_20260516}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
PYTHON_BIN=${PYTHON_BIN:-python3}

mkdir -p "$LOG_DIR"
export RUN_ROOT LOG_DIR TAG

"$PYTHON_BIN" - <<'PY'
import json, os, re, math, csv
import numpy as np
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
log_dir = Path(os.environ["LOG_DIR"])
tag = os.environ["TAG"]

def load_metric(run_dir):
    p = run_dir / "test_eval" / "metrics.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None

def bootstrap_ci(deltas, n=10000, ci=0.95):
    if not deltas:
        return float("nan"), float("nan")
    d = np.array(deltas, dtype=float)
    rng = np.random.default_rng(42)
    boot = rng.choice(d, size=(n, len(d)), replace=True).mean(axis=1)
    lo = float(np.percentile(boot, (1 - ci) / 2 * 100))
    hi = float(np.percentile(boot, (1 + ci) / 2 * 100))
    return lo, hi

VARIANTS = ["mid", "3slice", "proj", "drr"]
METHODS = ["teacher", "supervised", "plain_kd", "gated_kd"]

def parse_name(name):
    m = re.match(r"^(?P<variant>mid|3slice|proj|drr)_f(?P<fold>\d+)_s(?P<seed>\d+)_(?P<role>teacher|supervised|plain_kd|gated_kd_thr\d+)$", name)
    if not m:
        return None
    role = m.group("role")
    if role.startswith("gated_kd"):
        role = "gated_kd"
    return {
        "variant": m.group("variant"),
        "fold": int(m.group("fold")),
        "seed": int(m.group("seed")),
        "role": role,
    }

runs = []
for d in sorted(run_root.iterdir()):
    if not d.is_dir():
        continue
    parsed = parse_name(d.name)
    if parsed is None:
        continue
    metric = load_metric(d)
    if metric is None:
        continue
    ba = metric.get("balanced_accuracy", metric.get("val_balanced_accuracy", float("nan")))
    f1 = metric.get("macro_f1", metric.get("val_macro_f1", float("nan")))
    spec = metric.get("specificity", metric.get("val_specificity", float("nan")))
    auc = metric.get("roc_auc", metric.get("val_roc_auc", float("nan")))
    acc = metric.get("accuracy", metric.get("val_accuracy", float("nan")))
    n_test = metric.get("n_test", metric.get("num_samples", None))
    runs.append({
        "name": d.name, **parsed,
        "ba": float(ba) if ba is not None else float("nan"),
        "macro_f1": float(f1) if f1 is not None else float("nan"),
        "specificity": float(spec) if spec is not None else float("nan"),
        "roc_auc": float(auc) if auc is not None else float("nan"),
        "accuracy": float(acc) if acc is not None else float("nan"),
        "n_test": n_test,
    })

print(f"Loaded {len(runs)} test_eval results from {run_root}")

# Per-variant per-method summary
summary_rows = []
for variant in VARIANTS:
    for method in METHODS:
        subset = [r for r in runs if r["variant"] == variant and r["role"] == method]
        if not subset:
            continue
        bas = [r["ba"] for r in subset if not math.isnan(r["ba"])]
        f1s = [r["macro_f1"] for r in subset if not math.isnan(r["macro_f1"])]
        specs = [r["specificity"] for r in subset if not math.isnan(r["specificity"])]
        aucs = [r["roc_auc"] for r in subset if not math.isnan(r["roc_auc"])]
        accs = [r["accuracy"] for r in subset if not math.isnan(r["accuracy"])]
        nts = [r["n_test"] for r in subset if r["n_test"] is not None]
        lo, hi = bootstrap_ci(bas) if bas else (float("nan"), float("nan"))
        summary_rows.append({
            "variant": variant,
            "method": method,
            "n": len(subset),
            "ba_mean": float(np.mean(bas)) if bas else float("nan"),
            "ba_ci_lo": lo,
            "ba_ci_hi": hi,
            "macro_f1_mean": float(np.mean(f1s)) if f1s else float("nan"),
            "specificity_mean": float(np.mean(specs)) if specs else float("nan"),
            "roc_auc_mean": float(np.mean(aucs)) if aucs else float("nan"),
            "accuracy_mean": float(np.mean(accs)) if accs else float("nan"),
            "n_test_mean": float(np.mean(nts)) if nts else float("nan"),
        })

# Paired deltas: per variant, build (fold,seed) -> {method: ba}
delta_rows = []
COMPARISONS = [
    ("gated_kd", "supervised", "gated_vs_supervised"),
    ("gated_kd", "plain_kd", "gated_vs_plain"),
    ("teacher", "supervised", "teacher_vs_supervised"),
    ("plain_kd", "supervised", "plain_vs_supervised"),
]
for variant in VARIANTS:
    cells = {}
    for r in runs:
        if r["variant"] != variant:
            continue
        key = (r["fold"], r["seed"])
        cells.setdefault(key, {})[r["role"]] = r
    for left, right, label in COMPARISONS:
        deltas_ba = []; deltas_f1 = []; deltas_spec = []
        for key, methods in cells.items():
            if left in methods and right in methods:
                a = methods[left]; b = methods[right]
                if not math.isnan(a["ba"]) and not math.isnan(b["ba"]):
                    deltas_ba.append(a["ba"] - b["ba"])
                if not math.isnan(a["macro_f1"]) and not math.isnan(b["macro_f1"]):
                    deltas_f1.append(a["macro_f1"] - b["macro_f1"])
                if not math.isnan(a["specificity"]) and not math.isnan(b["specificity"]):
                    deltas_spec.append(a["specificity"] - b["specificity"])
        if not deltas_ba:
            continue
        lo, hi = bootstrap_ci(deltas_ba)
        mean_d = float(np.mean(deltas_ba))
        pos = sum(d > 0 for d in deltas_ba)
        neg = sum(d < 0 for d in deltas_ba)
        zero = sum(d == 0 for d in deltas_ba)
        decision = mean_d >= 0.03 and lo > 0
        delta_rows.append({
            "variant": variant,
            "comparison": label,
            "n": len(deltas_ba),
            "delta_ba_mean": mean_d,
            "delta_ba_ci_lo": lo,
            "delta_ba_ci_hi": hi,
            "positive": pos, "zero": zero, "negative": neg,
            "delta_macro_f1_mean": float(np.mean(deltas_f1)) if deltas_f1 else float("nan"),
            "delta_specificity_mean": float(np.mean(deltas_spec)) if deltas_spec else float("nan"),
            "decision_pass": decision,
        })

# Write CSVs
summary_csv = log_dir / "bimcv_full_paired_summary.csv"
with open(summary_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys())) if summary_rows else None
    if w:
        w.writeheader(); w.writerows(summary_rows)
delta_csv = log_dir / "bimcv_full_paired_deltas.csv"
with open(delta_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(delta_rows[0].keys())) if delta_rows else None
    if w:
        w.writeheader(); w.writerows(delta_rows)

# Status TSV
status_tsv = log_dir / "bimcv_full_paired_status.tsv"
with open(status_tsv, "w") as f:
    f.write("variant\tmethod\tfold\tseed\tba\tspecificity\troc_auc\n")
    for r in sorted(runs, key=lambda x: (x["variant"], x["fold"], x["seed"], x["role"])):
        f.write(f"{r['variant']}\t{r['role']}\t{r['fold']}\t{r['seed']}\t{r['ba']:.4f}\t{r['specificity']:.4f}\t{r['roc_auc']:.4f}\n")

# Decision report markdown
lines = [
    f"# Stage A 510-Patient Extended Paired CV Decision Report\n\n",
    f"Generated from `{run_root}` for tag `{tag}`.\n\n",
    f"## Run completion\n\n",
    f"- Completed test metrics: {len(runs)}/240.\n",
    f"- Cohort: BIMCV 113+/397- = 510 patients (4.5x previous 226 balanced).\n",
    f"- Execution: 4x RTX 3090, batch_size=512, num_workers=8, concurrency=4 per GPU, weighted-CE + weighted sampler for 3.5:1 imbalance.\n\n",
    f"## Mean test metrics\n\n",
    f"| Variant | Method | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |\n",
    f"|---|---:|---:|---:|---:|---:|---:|\n",
]
for r in summary_rows:
    lines.append(
        f"| {r['variant']} | {r['method']} | {r['n']} | "
        f"{r['ba_mean']:.4f} [{r['ba_ci_lo']:.4f}, {r['ba_ci_hi']:.4f}] | "
        f"{r['macro_f1_mean']:.4f} | {r['specificity_mean']:.4f} | {r['roc_auc_mean']:.4f} |\n"
    )

lines.append("\n## Paired decision deltas (pre-specified gate: mean DeltaBA >= +0.03 AND CI lower > 0)\n\n")
lines.append("| Variant | Comparison | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |\n|---|---|---:|---:|---:|---:|---:|---:|\n")
for r in delta_rows:
    pass_str = "YES" if r["decision_pass"] else "NO"
    lines.append(
        f"| {r['variant']} | {r['comparison']} | {r['n']} | "
        f"{r['delta_ba_mean']:+.4f} [{r['delta_ba_ci_lo']:+.4f}, {r['delta_ba_ci_hi']:+.4f}] | "
        f"{r['positive']}/{r['zero']}/{r['negative']} | "
        f"{r['delta_macro_f1_mean']:+.4f} | {r['delta_specificity_mean']:+.4f} | {pass_str} |\n"
    )

passes = sum(1 for r in delta_rows if r["decision_pass"])
gated_passes = sum(1 for r in delta_rows if r["decision_pass"] and r["comparison"] == "gated_vs_supervised")

lines.append("\n## Decision\n\n")
lines.append(f"- Total comparisons passing pre-specified gate: {passes}/{len(delta_rows)}\n")
lines.append(f"- Gated_vs_supervised comparisons passing: {gated_passes}/{len(VARIANTS)}\n\n")
if gated_passes > 0:
    lines.append("**VALIDATED**: at least one (teacher, gated KD) configuration passes the pre-specified gate on the 510-patient extended cohort. JDCNet GAP-KD framework has demonstrated cross-modal advantage at this cohort scale.\n")
else:
    lines.append("**NOT YET VALIDATED**: no gated_vs_supervised comparison passes the gate on the 510-patient cohort. Trigger Stage B (MIDRC 559 full processing) or Stage C (X-ray pretrain) per decision tree.\n")

report_path = log_dir / "decision_report.md"
report_path.write_text("".join(lines))
print(f"wrote summary CSV   : {summary_csv}")
print(f"wrote deltas CSV    : {delta_csv}")
print(f"wrote status TSV    : {status_tsv}")
print(f"wrote decision .md  : {report_path}")
PY
