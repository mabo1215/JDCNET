#!/usr/bin/env bash
set -euo pipefail
# Summarize contrastive alignment cross-modal experiment.
# Pulls test_eval/metrics.json from both the contrastive run root and the
# Stage A supervised baseline run root, and writes per-(variant, temperature)
# decision deltas under the same pre-specified gate (mean DeltaBA >= +0.03,
# 95% bootstrap CI lower bound > 0).

TAG=${TAG:-bimcv_contrastive_cv_20260516}
SOURCE_TAG=${SOURCE_TAG:-bimcv_full_paired_cv_20260516}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
SUP_RUN_ROOT=${SUP_RUN_ROOT:-/data1/midrc/runs/${SOURCE_TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
PYTHON_BIN=${PYTHON_BIN:-python3}

mkdir -p "$LOG_DIR"
export RUN_ROOT SUP_RUN_ROOT LOG_DIR TAG

"$PYTHON_BIN" - <<'PY'
import json, os, re, math, csv
import numpy as np
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
sup_run_root = Path(os.environ["SUP_RUN_ROOT"])
log_dir = Path(os.environ["LOG_DIR"])
tag = os.environ["TAG"]


def load_metric(run_dir):
    p = run_dir / "test_eval" / "metrics.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
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


def parse_contrastive_name(name):
    m = re.match(
        r"^(?P<variant>mid|3slice|proj|drr)_f(?P<fold>\d+)_s(?P<seed>\d+)_contrastive_t(?P<tau>\d+)$",
        name,
    )
    if not m:
        return None
    return {
        "variant": m.group("variant"),
        "fold": int(m.group("fold")),
        "seed": int(m.group("seed")),
        "tau": int(m.group("tau")) / 100.0,
    }


def parse_supervised_name(name):
    m = re.match(
        r"^(?P<variant>mid|3slice|proj|drr)_f(?P<fold>\d+)_s(?P<seed>\d+)_supervised$",
        name,
    )
    if not m:
        return None
    return {
        "variant": m.group("variant"),
        "fold": int(m.group("fold")),
        "seed": int(m.group("seed")),
    }


def collect(run_root_path, parser):
    out = []
    if not run_root_path.exists():
        return out
    for d in sorted(run_root_path.iterdir()):
        if not d.is_dir():
            continue
        parsed = parser(d.name)
        if parsed is None:
            continue
        metric = load_metric(d)
        if metric is None:
            continue
        ba = metric.get("balanced_accuracy", float("nan"))
        f1 = metric.get("macro_f1", float("nan"))
        spec = metric.get("specificity", float("nan"))
        auc = metric.get("roc_auc", float("nan"))
        acc = metric.get("accuracy", float("nan"))
        out.append({
            "name": d.name, **parsed,
            "ba": float(ba) if ba is not None else float("nan"),
            "macro_f1": float(f1) if f1 is not None else float("nan"),
            "specificity": float(spec) if spec is not None else float("nan"),
            "roc_auc": float(auc) if auc is not None else float("nan"),
            "accuracy": float(acc) if acc is not None else float("nan"),
        })
    return out


contrastive_runs = collect(run_root, parse_contrastive_name)
supervised_runs = collect(sup_run_root, parse_supervised_name)

print(f"contrastive runs loaded: {len(contrastive_runs)} from {run_root}")
print(f"supervised runs loaded : {len(supervised_runs)} from {sup_run_root}")

sup_index = {(r["variant"], r["fold"], r["seed"]): r for r in supervised_runs}

VARIANTS = sorted({r["variant"] for r in contrastive_runs})
TAUS = sorted({round(r["tau"], 4) for r in contrastive_runs})

summary_rows = []
delta_rows = []

for variant in VARIANTS:
    sup_subset = [r for r in supervised_runs if r["variant"] == variant]
    sup_bas = [r["ba"] for r in sup_subset if not math.isnan(r["ba"])]
    if sup_bas:
        lo, hi = bootstrap_ci(sup_bas)
        summary_rows.append({
            "variant": variant, "method": "supervised", "tau": "-",
            "n": len(sup_subset),
            "ba_mean": float(np.mean(sup_bas)),
            "ba_ci_lo": lo, "ba_ci_hi": hi,
            "macro_f1_mean": float(np.mean([r["macro_f1"] for r in sup_subset if not math.isnan(r["macro_f1"])])),
            "specificity_mean": float(np.mean([r["specificity"] for r in sup_subset if not math.isnan(r["specificity"])])),
            "roc_auc_mean": float(np.mean([r["roc_auc"] for r in sup_subset if not math.isnan(r["roc_auc"])])),
            "accuracy_mean": float(np.mean([r["accuracy"] for r in sup_subset if not math.isnan(r["accuracy"])])),
        })

    for tau in TAUS:
        c_subset = [r for r in contrastive_runs if r["variant"] == variant and round(r["tau"], 4) == tau]
        if not c_subset:
            continue
        bas = [r["ba"] for r in c_subset if not math.isnan(r["ba"])]
        if not bas:
            continue
        lo, hi = bootstrap_ci(bas)
        summary_rows.append({
            "variant": variant, "method": "contrastive", "tau": f"{tau:.2f}",
            "n": len(c_subset),
            "ba_mean": float(np.mean(bas)),
            "ba_ci_lo": lo, "ba_ci_hi": hi,
            "macro_f1_mean": float(np.mean([r["macro_f1"] for r in c_subset if not math.isnan(r["macro_f1"])])),
            "specificity_mean": float(np.mean([r["specificity"] for r in c_subset if not math.isnan(r["specificity"])])),
            "roc_auc_mean": float(np.mean([r["roc_auc"] for r in c_subset if not math.isnan(r["roc_auc"])])),
            "accuracy_mean": float(np.mean([r["accuracy"] for r in c_subset if not math.isnan(r["accuracy"])])),
        })

        deltas_ba = []; deltas_f1 = []; deltas_spec = []
        for r in c_subset:
            key = (r["variant"], r["fold"], r["seed"])
            s = sup_index.get(key)
            if s is None:
                continue
            if not math.isnan(r["ba"]) and not math.isnan(s["ba"]):
                deltas_ba.append(r["ba"] - s["ba"])
            if not math.isnan(r["macro_f1"]) and not math.isnan(s["macro_f1"]):
                deltas_f1.append(r["macro_f1"] - s["macro_f1"])
            if not math.isnan(r["specificity"]) and not math.isnan(s["specificity"]):
                deltas_spec.append(r["specificity"] - s["specificity"])
        if not deltas_ba:
            continue
        lo_d, hi_d = bootstrap_ci(deltas_ba)
        mean_d = float(np.mean(deltas_ba))
        pos = sum(1 for d in deltas_ba if d > 0)
        neg = sum(1 for d in deltas_ba if d < 0)
        zero = sum(1 for d in deltas_ba if d == 0)
        decision = mean_d >= 0.03 and lo_d > 0
        delta_rows.append({
            "variant": variant,
            "tau": f"{tau:.2f}",
            "comparison": "contrastive_vs_supervised",
            "n": len(deltas_ba),
            "delta_ba_mean": mean_d,
            "delta_ba_ci_lo": lo_d,
            "delta_ba_ci_hi": hi_d,
            "positive": pos, "zero": zero, "negative": neg,
            "delta_macro_f1_mean": float(np.mean(deltas_f1)) if deltas_f1 else float("nan"),
            "delta_specificity_mean": float(np.mean(deltas_spec)) if deltas_spec else float("nan"),
            "decision_pass": decision,
        })

summary_csv = log_dir / "bimcv_contrastive_summary.csv"
if summary_rows:
    with open(summary_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader(); w.writerows(summary_rows)
delta_csv = log_dir / "bimcv_contrastive_deltas.csv"
if delta_rows:
    with open(delta_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(delta_rows[0].keys()))
        w.writeheader(); w.writerows(delta_rows)

status_tsv = log_dir / "bimcv_contrastive_status.tsv"
with open(status_tsv, "w") as f:
    f.write("variant\tmethod\ttau\tfold\tseed\tba\tspecificity\troc_auc\n")
    for r in sorted(contrastive_runs, key=lambda x: (x["variant"], round(x["tau"], 4), x["fold"], x["seed"])):
        f.write(f"{r['variant']}\tcontrastive\t{r['tau']:.2f}\t{r['fold']}\t{r['seed']}\t{r['ba']:.4f}\t{r['specificity']:.4f}\t{r['roc_auc']:.4f}\n")
    for r in sorted(supervised_runs, key=lambda x: (x["variant"], x["fold"], x["seed"])):
        f.write(f"{r['variant']}\tsupervised\t-\t{r['fold']}\t{r['seed']}\t{r['ba']:.4f}\t{r['specificity']:.4f}\t{r['roc_auc']:.4f}\n")

# Decision report markdown
n_total = len(contrastive_runs)
lines = [
    f"# Method 1: Cross-Modal Contrastive Alignment Decision Report\n\n",
    f"Generated from `{run_root}` for tag `{tag}`. Supervised baseline pulled from `{sup_run_root}`.\n\n",
    f"## Run completion\n\n",
    f"- Contrastive runs with test_eval completed: {n_total}\n",
    f"- Cohort: BIMCV 510 paired patients (113+/397-)\n",
    f"- Stage 1 InfoNCE pretrain on (X-ray, CT) pairs; Stage 2 supervised fine-tune of X-ray encoder + classifier\n",
    f"- Hardware: 4x RTX 3090, AMP fp16\n\n",
    f"## Mean test metrics\n\n",
    f"| Variant | Method | tau | n | BA mean [95% CI] | Macro-F1 | Specificity | ROC-AUC |\n",
    f"|---|---|---:|---:|---:|---:|---:|---:|\n",
]
for r in summary_rows:
    lines.append(
        f"| {r['variant']} | {r['method']} | {r['tau']} | {r['n']} | "
        f"{r['ba_mean']:.4f} [{r['ba_ci_lo']:.4f}, {r['ba_ci_hi']:.4f}] | "
        f"{r['macro_f1_mean']:.4f} | {r['specificity_mean']:.4f} | {r['roc_auc_mean']:.4f} |\n"
    )

lines.append(
    "\n## Paired decision deltas vs supervised baseline (gate: mean DeltaBA >= +0.03 AND CI lower > 0)\n\n"
)
lines.append(
    "| Variant | tau | Comparison | n | Delta BA mean [95% CI] | +/0/- | Delta F1 | Delta Spec | Pass |\n"
    "|---|---:|---|---:|---:|---:|---:|---:|---:|\n"
)
for r in delta_rows:
    pass_str = "YES" if r["decision_pass"] else "NO"
    lines.append(
        f"| {r['variant']} | {r['tau']} | {r['comparison']} | {r['n']} | "
        f"{r['delta_ba_mean']:+.4f} [{r['delta_ba_ci_lo']:+.4f}, {r['delta_ba_ci_hi']:+.4f}] | "
        f"{r['positive']}/{r['zero']}/{r['negative']} | "
        f"{r['delta_macro_f1_mean']:+.4f} | {r['delta_specificity_mean']:+.4f} | {pass_str} |\n"
    )

passes = sum(1 for r in delta_rows if r["decision_pass"])
lines.append("\n## Decision\n\n")
lines.append(f"- Total contrastive comparisons passing pre-specified gate: {passes}/{len(delta_rows)}\n\n")
if passes > 0:
    lines.append(
        "**VALIDATED**: at least one (teacher, temperature) configuration of the cross-modal "
        "contrastive alignment passes the pre-specified gate on the 510-patient BIMCV paired cohort. "
        "Method 1 has demonstrated cross-modal advantage at this cohort scale.\n"
    )
else:
    lines.append(
        "**NOT VALIDATED**: no contrastive configuration passes the gate on the 510-patient cohort. "
        "Continue to Method 2 (CT pseudo-label semi-supervised) per the recommended execution order.\n"
    )

report_path = log_dir / "decision_report.md"
report_path.write_text("".join(lines))
print(f"wrote summary CSV : {summary_csv}")
print(f"wrote deltas  CSV : {delta_csv}")
print(f"wrote status  TSV : {status_tsv}")
print(f"wrote decision MD : {report_path}")
PY
