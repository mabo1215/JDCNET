"""Wilcoxon signed-rank, BCa bootstrap CI, and rank-stability reporting.

Reads per-resample / per-seed result rows from a CSV and emits a LaTeX-ready
summary table together with a Wilcoxon pairwise matrix and a rank-stability
diagnostic between fixed-split and resampled rankings. Designed to be the
statistical backbone of the revised IEEE TCSVT submission.

Input CSV schema (one row per (method, resample_id, seed) tuple):
    method,resample_id,seed,accuracy,macro_f1,balanced_accuracy,specificity,mcc,pr_auc

Usage:
    python -m jdcnet_exp.statistical_report \
        --resampling-csv runs/covid_resampling/per_run_metrics.csv \
        --fixed-split-csv runs/covid_matrix/per_run_metrics.csv \
        --metrics balanced_accuracy macro_f1 mcc \
        --output-dir paper/figs/generated
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def median_iqr(values: np.ndarray) -> tuple[float, float, float]:
    return float(np.median(values)), float(np.percentile(values, 25)), float(np.percentile(values, 75))


def bca_bootstrap_ci(values: np.ndarray, n_boot: int = 5000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    """Bias-corrected and accelerated bootstrap confidence interval for the mean."""
    if values.size < 2:
        return float(values[0]) if values.size else float("nan"), float(values[0]) if values.size else float("nan")
    rng = np.random.default_rng(seed)
    n = values.size
    boot_means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_means[i] = values[idx].mean()
    point = values.mean()
    z0 = stats.norm.ppf((boot_means < point).mean()) if 0 < (boot_means < point).mean() < 1 else 0.0
    jack = np.array([np.delete(values, i).mean() for i in range(n)])
    jack_mean = jack.mean()
    num = ((jack_mean - jack) ** 3).sum()
    den = 6.0 * (((jack_mean - jack) ** 2).sum() ** 1.5 + 1e-12)
    a_hat = num / den
    z_lo = stats.norm.ppf(alpha / 2)
    z_hi = stats.norm.ppf(1 - alpha / 2)
    a_lo = stats.norm.cdf(z0 + (z0 + z_lo) / (1 - a_hat * (z0 + z_lo)))
    a_hi = stats.norm.cdf(z0 + (z0 + z_hi) / (1 - a_hat * (z0 + z_hi)))
    lo = float(np.percentile(boot_means, 100 * a_lo))
    hi = float(np.percentile(boot_means, 100 * a_hi))
    return lo, hi


def wilcoxon_paired(method_a: np.ndarray, method_b: np.ndarray) -> dict[str, float]:
    """Wilcoxon signed-rank test on paired per-resample differences."""
    diffs = method_a - method_b
    nonzero = diffs[diffs != 0]
    if nonzero.size < 1:
        return {"statistic": float("nan"), "p_value": 1.0, "n_paired": int(diffs.size), "n_nonzero": 0,
                "median_diff": float(np.median(diffs)) if diffs.size else float("nan")}
    try:
        result = stats.wilcoxon(method_a, method_b, alternative="two-sided", zero_method="wilcox")
        return {"statistic": float(result.statistic), "p_value": float(result.pvalue),
                "n_paired": int(diffs.size), "n_nonzero": int(nonzero.size),
                "median_diff": float(np.median(diffs))}
    except ValueError as exc:
        return {"statistic": float("nan"), "p_value": 1.0, "n_paired": int(diffs.size),
                "n_nonzero": int(nonzero.size), "median_diff": float(np.median(diffs)),
                "error": str(exc)}


def rank_correlation(fixed_means: pd.Series, resample_means: pd.Series) -> dict[str, float]:
    common = fixed_means.index.intersection(resample_means.index)
    a = fixed_means.loc[common].rank(ascending=False)
    b = resample_means.loc[common].rank(ascending=False)
    spearman = stats.spearmanr(a, b)
    kendall = stats.kendalltau(a, b)
    return {
        "n_methods": int(common.size),
        "spearman_rho": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
        "kendall_tau": float(kendall.statistic),
        "kendall_p": float(kendall.pvalue),
    }


def latex_table(summary: pd.DataFrame, metric: str) -> str:
    lines = [
        "\\begin{table*}[t]",
        f"\\caption{{Per-method {metric} on the same-case resampling cohort. "
        "We report median, interquartile range, and BCa bootstrap 95\\% confidence "
        "interval over the resamples; mean$\\pm$SD is included for compatibility "
        "with prior versions of this paper. The Wilcoxon and rank-stability "
        "diagnostics are reported separately.}",
        f"\\label{{tab:{metric}_resampling_stats}}",
        "\\centering",
        "\\begin{tabular}{|l|c|c|c|c|}",
        "\\hline",
        "Method & Median [IQR] & 95\\% BCa CI & Mean $\\pm$ SD & $n$ resamples \\\\ \\hline",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"{row['method']} & "
            f"${row['median']:.3f}$ [${row['q1']:.3f}$, ${row['q3']:.3f}$] & "
            f"[${row['ci_lo']:.3f}$, ${row['ci_hi']:.3f}$] & "
            f"${row['mean']:.3f} \\pm {row['std']:.3f}$ & "
            f"{int(row['n'])} \\\\ \\hline"
        )
    lines += ["\\end{tabular}", "\\end{table*}"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resampling-csv", required=True)
    ap.add_argument("--fixed-split-csv", required=False, default=None)
    ap.add_argument("--metrics", nargs="+", default=["balanced_accuracy", "macro_f1", "accuracy"])
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--n-boot", type=int, default=5000)
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.resampling_csv)

    summary_payload: dict[str, object] = {"metrics": {}, "wilcoxon": {}, "rank_stability": {}}

    for metric in args.metrics:
        if metric not in df.columns:
            print(f"[warn] metric {metric} not in CSV; skipping")
            continue
        rows = []
        for method, sub in df.groupby("method"):
            values = sub[metric].to_numpy(dtype=float)
            med, q1, q3 = median_iqr(values)
            lo, hi = bca_bootstrap_ci(values, n_boot=args.n_boot, seed=42)
            rows.append({
                "method": method,
                "median": med, "q1": q1, "q3": q3,
                "ci_lo": lo, "ci_hi": hi,
                "mean": float(values.mean()),
                "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
                "n": int(values.size),
            })
        summary = pd.DataFrame(rows).sort_values("median", ascending=False)
        summary.to_csv(out / f"resampling_summary_{metric}.csv", index=False)
        (out / f"resampling_summary_{metric}.tex").write_text(latex_table(summary, metric), encoding="utf-8")
        summary_payload["metrics"][metric] = summary.to_dict(orient="records")

        # Wilcoxon pairwise matrix
        methods = sorted(df["method"].unique())
        pivot = df.pivot_table(index="resample_id", columns="method", values=metric, aggfunc="mean")
        pairwise: dict[str, dict[str, dict[str, float]]] = {}
        for a in methods:
            pairwise[a] = {}
            for b in methods:
                if a == b:
                    continue
                paired = pivot[[a, b]].dropna()
                if paired.empty:
                    continue
                pairwise[a][b] = wilcoxon_paired(paired[a].to_numpy(), paired[b].to_numpy())
        summary_payload["wilcoxon"][metric] = pairwise

        # Rank stability vs fixed-split, if available
        if args.fixed_split_csv:
            fixed = pd.read_csv(args.fixed_split_csv)
            if metric in fixed.columns:
                fixed_means = fixed.groupby("method")[metric].mean()
                resample_means = df.groupby("method")[metric].mean()
                summary_payload["rank_stability"][metric] = rank_correlation(fixed_means, resample_means)

    (out / "statistical_report.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"[done] wrote LaTeX tables and JSON summary to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
