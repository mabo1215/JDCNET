"""Statistics regenerated from archived records for the third manuscript revision.

The script only reads aggregate records under ``src/records`` (no images, no
checkpoints) and writes a JSON summary to ``src/records/derived``. It covers:

* absolute test-fold metrics of the supervised baseline and of the initial
  (pre-planned) 8-configuration JDCNet grid on the 510-patient cohort;
* directly computed per-configuration p-values (sign test from the recorded
  fold/seed win counts for all 16 configurations; paired t-test, Wilcoxon
  signed-rank test and bootstrap for the 8 configurations whose per-fold
  records are archived) and their Holm / Benjamini-Hochberg / Sidak adjustment;
* a Monte Carlo illustration of selection inflation when the best of 16
  configurations is reported;
* patient-level confidence intervals for the external stress test computed
  from the class counts and the reported point estimates;
* bounds on the information discarded by the hard (argmax) target.

Usage:
    python -m jdcnet_exp.revision_stats
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records"
OUT_DIR = RECORDS / "derived"

N_BOOT = 10_000
RNG_SEED = 20261013

# CT-only reference deltas on the 510-patient cohort (Stage A run report).
CT_REFERENCE_DELTA = {"mid": 0.0450, "3slice": 0.0511}

# External stress test: class counts and checkpoint-averaged point estimates
# (run log of the external X-ray-only evaluation).
EXTERNAL_N_POS = 63
EXTERNAL_N_NEG = 63
EXTERNAL_POINT = {
    "supervised": {"ba": 0.492, "auc": 0.486},
    "jdcnet_3slice_softkl": {"ba": 0.498, "auc": 0.509},
    "jdcnet_mid_hard": {"ba": 0.494, "auc": 0.477},
}


def _bootstrap_mean_ci(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    idx = rng.integers(0, len(values), size=(N_BOOT, len(values)))
    means = values[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _bootstrap_p(values: np.ndarray, rng: np.random.Generator) -> float:
    """Two-sided percentile-bootstrap p-value for H0: mean = 0 (shift method)."""
    centered = values - values.mean()
    idx = rng.integers(0, len(values), size=(N_BOOT, len(values)))
    null_means = centered[idx].mean(axis=1)
    return float((np.sum(np.abs(null_means) >= abs(values.mean())) + 1) / (N_BOOT + 1))


def _sign_test_p(positive: int, negative: int) -> float:
    n = positive + negative
    if n == 0:
        return 1.0
    return float(stats.binomtest(positive, n, 0.5, alternative="two-sided").pvalue)


def _wald_p_from_ci(mean: float, lo: float, hi: float) -> tuple[float, float]:
    se = (hi - lo) / (2.0 * 1.959964)
    z = mean / se
    return float(z), float(2.0 * stats.norm.sf(abs(z)))


def _holm(pvalues: np.ndarray) -> np.ndarray:
    m = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvalues[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted


def _bh(pvalues: np.ndarray) -> np.ndarray:
    m = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(m)
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        running = min(running, pvalues[idx] * m / (rank + 1))
        adjusted[idx] = running
    return adjusted


def _load_initial_grid() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(RECORDS / "jdcnet510_initial_grid_per_fold.tsv", sep="\t")
    supervised = (
        frame[(frame["method"] == "supervised") & (frame["variant"] == "mid")]
        .drop_duplicates(["fold", "seed"])
        .set_index(["fold", "seed"])
        .sort_index()
    )
    jdcnet = frame[frame["method"] == "pseudolabel"].copy()
    return supervised, jdcnet


def _absolute_summary(ba: np.ndarray, spec: np.ndarray, auc: np.ndarray) -> dict[str, float]:
    sens = 2.0 * ba - spec
    return {
        "ba_mean": float(ba.mean()),
        "ba_sd": float(ba.std(ddof=1)),
        "auc_mean": float(auc.mean()),
        "auc_sd": float(auc.std(ddof=1)),
        "spec_mean": float(spec.mean()),
        "spec_sd": float(spec.std(ddof=1)),
        "sens_mean": float(sens.mean()),
        "sens_sd": float(sens.std(ddof=1)),
    }


def initial_grid_statistics(rng: np.random.Generator) -> dict[str, object]:
    supervised, jdcnet = _load_initial_grid()
    sup_ba = supervised["ba"].to_numpy()
    result: dict[str, object] = {
        "supervised_absolute": _absolute_summary(
            sup_ba, supervised["specificity"].to_numpy(), supervised["roc_auc"].to_numpy()
        ),
        "cells": [],
    }

    delta_matrix = []
    abs_ba, abs_spec, abs_auc = [], [], []
    for (variant, tau, lam), group in jdcnet.groupby(["variant", "tau", "lambda"]):
        group = group.drop_duplicates(["fold", "seed"]).set_index(["fold", "seed"]).sort_index()
        group = group.loc[supervised.index]
        delta = group["ba"].to_numpy() - sup_ba
        delta_matrix.append(delta)
        abs_ba.append(group["ba"].to_numpy())
        abs_spec.append(group["specificity"].to_numpy())
        abs_auc.append(group["roc_auc"].to_numpy())
        sens = 2.0 * group["ba"].to_numpy() - group["specificity"].to_numpy()
        sup_sens = 2.0 * sup_ba - supervised["specificity"].to_numpy()
        lo, hi = _bootstrap_mean_ci(delta, rng)
        positive, negative = int(np.sum(delta > 0)), int(np.sum(delta < 0))
        result["cells"].append(
            {
                "teacher": variant,
                "tau": float(tau),
                "lambda": float(lam),
                "delta_ba_mean": float(delta.mean()),
                "delta_ba_ci_reproduced": [lo, hi],
                "positive": positive,
                "negative": negative,
                "p_sign": _sign_test_p(positive, negative),
                "p_paired_t": float(stats.ttest_1samp(delta, 0.0).pvalue),
                "p_wilcoxon": float(stats.wilcoxon(delta).pvalue),
                "p_bootstrap": _bootstrap_p(delta, rng),
                "delta_spec_mean": float((group["specificity"].to_numpy() - supervised["specificity"].to_numpy()).mean()),
                "delta_sens_mean": float((sens - sup_sens).mean()),
                "delta_auc_mean": float((group["roc_auc"].to_numpy() - supervised["roc_auc"].to_numpy()).mean()),
            }
        )

    delta_matrix = np.vstack(delta_matrix)
    corr = np.corrcoef(delta_matrix)
    off_diag = corr[~np.eye(len(corr), dtype=bool)]
    grid_delta = delta_matrix.mean(axis=0)
    lo, hi = _bootstrap_mean_ci(grid_delta, rng)
    result["initial_grid_average"] = {
        "description": "Per fold/seed average over the 8 pre-planned hard-target configurations minus the matched supervised baseline",
        "delta_ba_mean": float(grid_delta.mean()),
        "delta_ba_ci": [lo, hi],
        "positive": int(np.sum(grid_delta > 0)),
        "negative": int(np.sum(grid_delta < 0)),
        "p_paired_t": float(stats.ttest_1samp(grid_delta, 0.0).pvalue),
        "p_sign": _sign_test_p(int(np.sum(grid_delta > 0)), int(np.sum(grid_delta < 0))),
        "absolute": _absolute_summary(
            np.mean(abs_ba, axis=0), np.mean(abs_spec, axis=0), np.mean(abs_auc, axis=0)
        ),
    }
    result["between_configuration_delta_correlation"] = {
        "mean": float(off_diag.mean()),
        "min": float(off_diag.min()),
        "max": float(off_diag.max()),
    }
    return result


def full_grid_statistics(rho: float, rng: np.random.Generator) -> dict[str, object]:
    grid = pd.read_csv(RECORDS / "jdcnet510_grid_summary.csv")
    rows = []
    for _, row in grid.iterrows():
        z, p_wald = _wald_p_from_ci(row["delta_ba_mean"], row["delta_ba_ci_lo"], row["delta_ba_ci_hi"])
        rows.append(
            {
                "teacher": row["teacher"],
                "tau": float(row["tau"]),
                "lambda": float(row["lambda"]),
                "target": row["target"],
                "stage": row["stage"],
                "delta_ba_mean": float(row["delta_ba_mean"]),
                "ci": [float(row["delta_ba_ci_lo"]), float(row["delta_ba_ci_hi"])],
                "counts": [int(row["positive"]), int(row["zero"]), int(row["negative"])],
                "se_from_ci": float((row["delta_ba_ci_hi"] - row["delta_ba_ci_lo"]) / (2 * 1.959964)),
                "z_wald": z,
                "p_wald": p_wald,
                "p_sign": _sign_test_p(int(row["positive"]), int(row["negative"])),
            }
        )
    p_wald = np.array([r["p_wald"] for r in rows])
    p_sign = np.array([r["p_sign"] for r in rows])
    holm_wald, bh_wald = _holm(p_wald), _bh(p_wald)
    holm_sign, bh_sign = _holm(p_sign), _bh(p_sign)
    m = len(rows)
    for i, r in enumerate(rows):
        r["p_wald_holm"] = float(holm_wald[i])
        r["p_wald_bh"] = float(bh_wald[i])
        r["p_wald_sidak"] = float(1.0 - (1.0 - r["p_wald"]) ** m)
        r["p_sign_holm"] = float(holm_sign[i])
        r["p_sign_bh"] = float(bh_sign[i])
        r["passes_planned_gate"] = bool(r["delta_ba_mean"] >= 0.03 and r["ci"][0] > 0)

    means = np.array([r["delta_ba_mean"] for r in rows])
    ses = np.array([r["se_from_ci"] for r in rows])

    # Monte Carlo: expected maximum of 16 noisy estimates when every configuration
    # shares the same true effect (the grid average), with equicorrelated noise.
    def simulate_max(true_effect: float, correlation: float, n_sim: int = 200_000) -> dict[str, float]:
        cov = correlation * np.outer(ses, ses) + (1.0 - correlation) * np.diag(ses**2)
        draws = rng.multivariate_normal(np.full(m, true_effect), cov, size=n_sim)
        best = draws.max(axis=1)
        return {
            "true_effect": true_effect,
            "correlation": correlation,
            "expected_max": float(best.mean()),
            "p_max_ge_observed_best": float(np.mean(best >= means.max())),
            "p_at_least_two_pass_gate": float(
                np.mean(
                    np.sum((draws >= 0.03) & (draws - 1.959964 * ses > 0), axis=1) >= 2
                )
            ),
        }

    grid_mean = float(means.mean())
    hard = {(r["teacher"], r["tau"]): r["delta_ba_mean"] for r in rows if r["target"] == "hard" and r["lambda"] == 1.0}
    soft = {(r["teacher"], r["tau"]): r["delta_ba_mean"] for r in rows if r["target"] == "soft_kl"}
    matched = [soft[k] - hard[k] for k in soft]
    return {
        "configurations": rows,
        "n_configurations": m,
        "n_positive_means": int(np.sum(means > 0)),
        "grid_average_delta_ba": grid_mean,
        "selection_simulation": [
            simulate_max(0.0, 0.0),
            simulate_max(0.0, rho),
            simulate_max(grid_mean, 0.0),
            simulate_max(grid_mean, rho),
        ],
        "soft_minus_hard_matched_lambda1": {
            "pairs": {f"{k[0]}_tau{k[1]:.2f}": soft[k] - hard[k] for k in soft},
            "mean": float(np.mean(matched)),
        },
        "descriptive_recovery_ratio": {
            "3slice_softkl_best": 0.0345 / CT_REFERENCE_DELTA["3slice"],
            "mid_hard_best": 0.0329 / CT_REFERENCE_DELTA["mid"],
            "grid_average_vs_mean_ct_reference": grid_mean / np.mean(list(CT_REFERENCE_DELTA.values())),
        },
    }


def _hanley_mcneil_se(auc: float, n_pos: int, n_neg: int) -> float:
    q1 = auc / (2.0 - auc)
    q2 = 2.0 * auc * auc / (1.0 + auc)
    var = (auc * (1 - auc) + (n_pos - 1) * (q1 - auc**2) + (n_neg - 1) * (q2 - auc**2)) / (n_pos * n_neg)
    return math.sqrt(var)


def _wilson(p: float, n: int) -> tuple[float, float]:
    z = 1.959964
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def external_statistics() -> dict[str, object]:
    n = EXTERNAL_N_POS + EXTERNAL_N_NEG
    out: dict[str, object] = {"n_images": n, "models": {}, "differences_vs_supervised": {}}
    for name, point in EXTERNAL_POINT.items():
        # With 63/63 classes, BA equals accuracy, i.e. a proportion over 126 images.
        ba_lo, ba_hi = _wilson(point["ba"], n)
        se_auc = _hanley_mcneil_se(point["auc"], EXTERNAL_N_POS, EXTERNAL_N_NEG)
        out["models"][name] = {
            "ba": point["ba"],
            "ba_ci_wilson": [ba_lo, ba_hi],
            "ba_se": math.sqrt(point["ba"] * (1 - point["ba"]) / n),
            "auc": point["auc"],
            "auc_ci_hanley_mcneil": [point["auc"] - 1.959964 * se_auc, point["auc"] + 1.959964 * se_auc],
            "auc_se": se_auc,
        }
    sup = out["models"]["supervised"]
    for name in ("jdcnet_3slice_softkl", "jdcnet_mid_hard"):
        model = out["models"][name]
        d_ba = model["ba"] - sup["ba"]
        d_auc = model["auc"] - sup["auc"]
        se_ba_ind = math.sqrt(model["ba_se"] ** 2 + sup["ba_se"] ** 2)
        se_auc_ind = math.sqrt(model["auc_se"] ** 2 + sup["auc_se"] ** 2)
        out["differences_vs_supervised"][name] = {
            "delta_ba": d_ba,
            "delta_ba_in_images": d_ba * n,
            "delta_ba_ci_independence": [d_ba - 1.959964 * se_ba_ind, d_ba + 1.959964 * se_ba_ind],
            "delta_auc": d_auc,
            "delta_auc_ci_independence": [d_auc - 1.959964 * se_auc_ind, d_auc + 1.959964 * se_auc_ind],
        }
    return out


def hard_target_bounds() -> dict[str, object]:
    def binary_entropy_bits(p: float) -> float:
        return float(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))

    return {
        f"tau_{tau:.2f}": {
            "max_kl_onehot_vs_teacher_nats": float(-math.log(tau)),
            "max_discarded_teacher_entropy_bits": binary_entropy_bits(tau),
        }
        for tau in (0.70, 0.80)
    }


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    initial = initial_grid_statistics(rng)
    rho = initial["between_configuration_delta_correlation"]["mean"]
    summary = {
        "initial_grid": initial,
        "full_grid": full_grid_statistics(rho, rng),
        "external": external_statistics(),
        "hard_target_bounds": hard_target_bounds(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "revision_round3_stats.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
