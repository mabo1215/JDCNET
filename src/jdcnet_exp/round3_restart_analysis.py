"""Cell-level analyses of Experiment A (batch-128 supervised restarts) from recorded metrics.

Compares the 16 JDCNet configurations with (i) the batch-matched baseline r = 0,
(ii) the mean of the 16 supervised restarts in the same cell, and runs the
pre-specified nested-selection comparison (best of 16 by validation BA).

Usage:
    python -m jdcnet_exp.round3_restart_analysis
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(20261014)


def tests(d: np.ndarray) -> dict[str, object]:
    idx = RNG.integers(0, len(d), size=(10_000, len(d)))
    m = d[idx].mean(axis=1)
    pos, neg = int(np.sum(d > 1e-12)), int(np.sum(d < -1e-12))
    out = {"mean": float(d.mean()), "ci": [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))],
           "positive": pos, "zero": len(d) - pos - neg, "negative": neg, "p_t": float(stats.ttest_1samp(d, 0).pvalue)}
    try:
        out["p_wilcoxon"] = float(stats.wilcoxon(d).pvalue)
    except ValueError:
        out["p_wilcoxon"] = 1.0
    return out


def holm(p):
    p = np.asarray(p); order, adj, run = np.argsort(p), np.empty(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, (len(p) - r) * p[i]); adj[i] = min(1.0, run)
    return adj


def main() -> None:
    runs = pd.read_csv(ROOT / "records" / "runs510_per_run.csv", dtype={"tau": str, "lambda": str})
    sup = pd.read_csv(ROOT / "records" / "sup128_per_run.csv")
    cells = [(f, s) for f in range(5) for s in (42, 43, 44)]
    sup["cell"] = list(zip(sup.fold, sup.seed))
    jd = runs[runs.stage.str.startswith("jdcnet")].copy()
    jd["cell"] = list(zip(jd.fold.astype(int), jd.seed.astype(int)))
    jd["config"] = jd.variant + "|" + jd.tau + "|" + jd["lambda"] + "|" + jd.target
    sa = runs[(runs.stage == "stage_a") & (runs.variant == "mid") & (runs.method == "supervised")].copy()
    sa["cell"] = list(zip(sa.fold.astype(int), sa.seed.astype(int)))

    def by_cell(df, col="test_balanced_accuracy"):
        return np.array([df[df.cell == c][col].iloc[0] for c in cells])

    sup512 = by_cell(sa)
    r00 = by_cell(sup[sup.r == 0])
    rmean = np.array([sup[sup.cell == c].test_balanced_accuracy.mean() for c in cells])
    res = {"sup512_mean": float(sup512.mean()), "sup128_r00_mean": float(r00.mean()), "sup128_restart_mean": float(rmean.mean()),
           "sup128_within_cell_sd": float(sup.groupby("cell").test_balanced_accuracy.std().mean()),
           "sup128_r00_minus_sup512": tests(r00 - sup512), "sup128_restartmean_minus_sup512": tests(rmean - sup512)}

    cfgs = sorted(jd.config.unique())
    for name, base in (("vs_sup512", sup512), ("vs_sup128_r00", r00), ("vs_sup128_restart_mean", rmean)):
        rows = {c: tests(by_cell(jd[jd.config == c]) - base) for c in cfgs}
        for c, h in zip(cfgs, holm([rows[c]["p_t"] for c in cfgs])):
            rows[c]["p_t_holm"] = float(h)
        grid = np.mean([by_cell(jd[jd.config == c]) for c in cfgs], axis=0)
        rows["grid_average_16"] = tests(grid - base)
        res[name] = rows

    def nested(df, k=None):
        out = []
        for c in cells:
            g = df[df.cell == c]
            if k is not None:
                g = g[g.r < k]
            out.append(g.sort_values("val_balanced_accuracy", ascending=False).iloc[0].test_balanced_accuracy)
        return np.array(out)

    jd16 = nested(jd)
    jd8 = nested(jd[jd.stage == "jdcnet_initial"])
    s16 = nested(sup, 16)
    s8 = nested(sup, 8)
    res["nested"] = {"jdcnet16_mean": float(jd16.mean()), "sup128_best16_mean": float(s16.mean()),
                     "jdcnet16_minus_sup128best16": tests(jd16 - s16),
                     "jdcnet8_minus_sup128best8": tests(jd8 - s8),
                     "sup128best16_minus_sup128r00": tests(s16 - r00),
                     "jdcnet16_minus_sup128r00": tests(jd16 - r00)}
    out = ROOT / "records" / "derived" / "round3_restart_analysis.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")

    f = lambda t: f"{t['mean']:+.4f} [{t['ci'][0]:+.4f},{t['ci'][1]:+.4f}] {t['positive']}/{t['zero']}/{t['negative']} pt={t['p_t']:.4f}"
    print("means: sup512 %.4f  sup128 r00 %.4f  sup128 restart-mean %.4f  within-cell SD %.4f" % (
        res["sup512_mean"], res["sup128_r00_mean"], res["sup128_restart_mean"], res["sup128_within_cell_sd"]))
    print("r00 - sup512:", f(res["sup128_r00_minus_sup512"]))
    print("restart mean - sup512:", f(res["sup128_restartmean_minus_sup512"]))
    for name in ("vs_sup512", "vs_sup128_r00", "vs_sup128_restart_mean"):
        print("\nJDCNet", name)
        for c in sorted(cfgs, key=lambda c: -res[name][c]["mean"]):
            print(f"  {c:26s} {f(res[name][c])} holm={res[name][c]['p_t_holm']:.3f}")
        print("  grid average 16:", f(res[name]["grid_average_16"]))
    print("\nnested: jd16 %.4f sup best16 %.4f" % (res["nested"]["jdcnet16_mean"], res["nested"]["sup128_best16_mean"]))
    for k in ("jdcnet16_minus_sup128best16", "jdcnet8_minus_sup128best8", "sup128best16_minus_sup128r00", "jdcnet16_minus_sup128r00"):
        print(" ", k, f(res["nested"][k]))


if __name__ == "__main__":
    main()
