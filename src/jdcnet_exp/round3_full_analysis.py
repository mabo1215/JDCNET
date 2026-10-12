"""Full re-analysis of the 510-patient runs from per-run records.

Input: ``src/records/runs510_per_run.csv`` (see collect_run_records.py).
Output: ``src/records/derived/round3_full_analysis.json`` and a printed summary.

Analyses:
* absolute test-partition metrics for every row of the manuscript tables;
* paired differences against the supervised baseline of the same split with
  bootstrap CIs, win counts, paired t, Wilcoxon, sign, and bootstrap tests for
  all 16 JDCNet configurations, with Holm and Benjamini-Hochberg adjustment;
* configuration selection on the validation partition (nested selection):
  in every fold/seed cell the configuration with the highest validation BA is
  chosen and only its test BA is used;
* the Tibshirani-Tibshirani estimate of the optimism of the best configuration.

Usage:
    python -m jdcnet_exp.round3_full_analysis
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records"
OUT = RECORDS / "derived" / "round3_full_analysis.json"
N_BOOT = 10_000
RNG = np.random.default_rng(20261013)


def boot_ci(x: np.ndarray) -> list[float]:
    idx = RNG.integers(0, len(x), size=(N_BOOT, len(x)))
    m = x[idx].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def boot_p(x: np.ndarray) -> float:
    c = x - x.mean()
    idx = RNG.integers(0, len(x), size=(N_BOOT, len(x)))
    m = c[idx].mean(axis=1)
    return float((np.sum(np.abs(m) >= abs(x.mean())) + 1) / (N_BOOT + 1))


def tests(d: np.ndarray) -> dict[str, float]:
    pos, neg = int(np.sum(d > 1e-12)), int(np.sum(d < -1e-12))
    out = {
        "mean": float(d.mean()), "ci": boot_ci(d), "positive": pos, "zero": len(d) - pos - neg, "negative": neg,
        "p_t": float(stats.ttest_1samp(d, 0.0).pvalue),
        "p_sign": float(stats.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else 1.0,
        "p_boot": boot_p(d),
    }
    try:
        out["p_wilcoxon"] = float(stats.wilcoxon(d).pvalue)
    except ValueError:
        out["p_wilcoxon"] = 1.0
    return out


def holm(p: np.ndarray) -> np.ndarray:
    m, order, adj, run = len(p), np.argsort(p), np.empty(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def bh(p: np.ndarray) -> np.ndarray:
    m, order, adj, run = len(p), np.argsort(p), np.empty(len(p)), 1.0
    for r in range(m - 1, -1, -1):
        i = order[r]
        run = min(run, p[i] * m / (r + 1))
        adj[i] = run
    return adj


def absolute(g: pd.DataFrame) -> dict[str, float]:
    out = {}
    for k, col in [("ba", "test_balanced_accuracy"), ("auc", "test_roc_auc"), ("macro_f1", "test_macro_f1"),
                   ("sens", "test_recall"), ("spec", "test_specificity")]:
        out[k] = float(g[col].mean())
        out[k + "_sd"] = float(g[col].std(ddof=1))
    return out


def main() -> None:
    d = pd.read_csv(RECORDS / "runs510_per_run.csv", dtype={"tau": str, "lambda": str})
    d["cell"] = d["fold"].astype(str) + "_" + d["seed"].astype(str)
    res: dict[str, object] = {}

    a = d[d.stage == "stage_a"]
    sup = {v: g.set_index("cell").sort_index() for v, g in a[a.method == "supervised"].groupby("variant")}
    # identical supervised runs across variants?
    ref = sup["mid"]["test_balanced_accuracy"]
    res["supervised_identical_across_variants"] = {v: bool(np.allclose(s["test_balanced_accuracy"].values, ref.values)) for v, s in sup.items()}
    base = sup["mid"]
    cells = base.index
    res["supervised"] = absolute(base)

    rows = {}
    for (v, m), g in a.groupby(["variant", "method"]):
        g = g.set_index("cell").loc[cells]
        delta = g["test_balanced_accuracy"].values - sup[v]["test_balanced_accuracy"].loc[cells].values
        rows[f"stage_a/{v}/{m}"] = {"absolute": absolute(g), "delta": tests(delta)}
    res["stage_a"] = rows

    j = d[d.stage.str.startswith("jdcnet")].copy()
    j["config"] = j["variant"] + "|" + j["tau"] + "|" + j["lambda"] + "|" + j["target"]
    cfg_rows, deltas, val = {}, {}, {}
    for cfg, g in j.groupby("config"):
        v = cfg.split("|")[0]
        g = g.set_index("cell").loc[cells]
        dlt = g["test_balanced_accuracy"].values - sup[v]["test_balanced_accuracy"].loc[cells].values
        deltas[cfg] = dlt
        val[cfg] = g["val_balanced_accuracy"].values
        dsens = g["test_recall"].values - sup[v]["test_recall"].loc[cells].values
        dspec = g["test_specificity"].values - sup[v]["test_specificity"].loc[cells].values
        dauc = g["test_roc_auc"].values - sup[v]["test_roc_auc"].loc[cells].values
        cfg_rows[cfg] = {"stage": g["stage"].iloc[0], "absolute": absolute(g), "delta": tests(dlt),
                         "delta_sens": float(dsens.mean()), "delta_spec": float(dspec.mean()), "delta_auc": float(dauc.mean())}
    names = sorted(cfg_rows)
    for key in ("p_t", "p_wilcoxon", "p_boot", "p_sign"):
        p = np.array([cfg_rows[c]["delta"][key] for c in names])
        for c, h, b in zip(names, holm(p), bh(p)):
            cfg_rows[c]["delta"][key + "_holm"] = float(h)
            cfg_rows[c]["delta"][key + "_bh"] = float(b)
    res["jdcnet"] = cfg_rows
    D = np.vstack([deltas[c] for c in names])
    corr = np.corrcoef(D)
    res["jdcnet_delta_correlation_mean"] = float(corr[~np.eye(len(names), dtype=bool)].mean())
    res["grid_average"] = {"all16": tests(D.mean(axis=0)),
                           "initial8": tests(np.vstack([deltas[c] for c in names if cfg_rows[c]["stage"] == "jdcnet_initial"]).mean(axis=0))}

    # nested selection on the validation partition
    V = np.vstack([val[c] for c in names])
    def nested(subset):
        idx = [names.index(c) for c in subset]
        choice = np.array([idx[int(np.argmax(V[idx, k]))] for k in range(V.shape[1])])
        chosen = D[choice, np.arange(D.shape[1])]
        return {"delta": tests(chosen), "chosen_configs": [names[i] for i in choice]}
    res["nested_selection"] = {"all16": nested(names),
                               "initial8": nested([c for c in names if cfg_rows[c]["stage"] == "jdcnet_initial"])}
    # Tibshirani-Tibshirani optimism of the best-by-mean configuration
    best = int(np.argmax(D.mean(axis=1)))
    tt_bias = float(np.mean(D.max(axis=0) - D[best]))
    res["tibshirani_tibshirani"] = {"best_config": names[best], "best_mean": float(D[best].mean()),
                                    "bias": tt_bias, "adjusted": float(D[best].mean() - tt_bias)}

    for st, key in [("contrastive", "contrastive"), ("biomedclip_226", "biomedclip"), ("ct_variants_226", "ct_variants_226"), ("gated_scan_balanced", "gated_scan")]:
        res[key] = {f"{v}/{m}": absolute(g) for (v, m), g in d[d.stage == st].groupby(["variant", "method"], dropna=False)}
    c = d[d.stage == "contrastive"]
    res["contrastive_delta"] = {}
    for (v, m), g in c.groupby(["variant", "method"]):
        g = g.set_index("cell").loc[cells]
        res["contrastive_delta"][f"{v}/{m}"] = tests(g["test_balanced_accuracy"].values - sup[v]["test_balanced_accuracy"].loc[cells].values)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    def f(x):
        return f"{x:+.4f}"
    print("supervised identical across variants:", res["supervised_identical_across_variants"])
    print("SUP", {k: round(v, 4) for k, v in res["supervised"].items()})
    print("\nJDCNet configs (sorted by mean delta)")
    for cname in sorted(names, key=lambda c: -cfg_rows[c]["delta"]["mean"]):
        r = cfg_rows[cname]; t = r["delta"]
        print(f"{cname:28s} {r['stage'][7:]:12s} {f(t['mean'])} [{f(t['ci'][0])},{f(t['ci'][1])}] {t['positive']}/{t['zero']}/{t['negative']} "
              f"pt={t['p_t']:.3f} pw={t['p_wilcoxon']:.3f} pb={t['p_boot']:.3f} ps={t['p_sign']:.2f} holm_t={t['p_t_holm']:.3f} bh_t={t['p_t_bh']:.3f} "
              f"BA={r['absolute']['ba']:.3f} AUC={r['absolute']['auc']:.3f} F1={r['absolute']['macro_f1']:.3f} Se={r['absolute']['sens']:.3f} Sp={r['absolute']['spec']:.3f} "
              f"dSe={r['delta_sens']:+.3f} dSp={r['delta_spec']:+.3f} dAUC={r['delta_auc']:+.3f}")
    print("\ncorr", round(res["jdcnet_delta_correlation_mean"], 3))
    for k, v in res["grid_average"].items():
        print("grid", k, f(v["mean"]), [round(x, 4) for x in v["ci"]], v["positive"], v["negative"], "pt", round(v["p_t"], 4))
    for k, v in res["nested_selection"].items():
        t = v["delta"]
        print("nested", k, f(t["mean"]), [round(x, 4) for x in t["ci"]], t["positive"], t["zero"], t["negative"], "pt", round(t["p_t"], 4), "pw", round(t["p_wilcoxon"], 4))
        print("   chosen:", pd.Series(v["chosen_configs"]).value_counts().to_dict())
    print("TT", res["tibshirani_tibshirani"])
    print("\nStage A rows")
    for k, v in res["stage_a"].items():
        t = v["delta"]; ab = v["absolute"]
        print(f"{k:32s} {f(t['mean'])} [{f(t['ci'][0])},{f(t['ci'][1])}] {t['positive']}/{t['zero']}/{t['negative']} pt={t['p_t']:.4f} "
              f"BA={ab['ba']:.3f}({ab['ba_sd']:.3f}) AUC={ab['auc']:.3f} F1={ab['macro_f1']:.3f} Se={ab['sens']:.3f} Sp={ab['spec']:.3f}")
    print("\ncontrastive", {k: (round(v['mean'], 4), [round(x, 4) for x in v['ci']], v['positive'], v['zero'], v['negative'], round(v['p_t'], 3)) for k, v in res["contrastive_delta"].items()})


if __name__ == "__main__":
    main()
