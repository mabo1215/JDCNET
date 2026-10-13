"""Round-3 analyses from per-image predictions (see docs/round3_experiment_plan.md).

Inputs (local copies pulled from the 4x3090 host):
  --preds   directory with <group>/<run>__{test,midrc,all}.csv files
  --runs    src/records/runs510_per_run.csv (original runs, val/test metrics)
  --sup128  src/records/sup128_per_run.csv (new batch-128 supervised restarts)
Output: src/records/derived/round3_prediction_analysis.json (+ printed summary).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RNG = np.random.default_rng(20261013)
N_BOOT = 10_000


# ----------------------------------------------------------------- metrics
def ba(y: np.ndarray, p: np.ndarray, thr: float = 0.5) -> float:
    pred = (p > thr).astype(int)
    tpr = np.mean(pred[y == 1] == 1)
    tnr = np.mean(pred[y == 0] == 0)
    return float((tpr + tnr) / 2)


def auc(y: np.ndarray, p: np.ndarray) -> float:
    pos, neg = p[y == 1], p[y == 0]
    r = stats.rankdata(np.concatenate([pos, neg]))
    return float((r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def delong(y: np.ndarray, pa: np.ndarray, pb: np.ndarray) -> dict[str, float]:
    """Paired DeLong test for two correlated ROC AUCs."""
    pos, neg = y == 1, y == 0
    m, n = pos.sum(), neg.sum()
    out = {}
    v10, v01, aucs = [], [], []
    for p in (pa, pb):
        X, Y = p[pos], p[neg]
        psi = (X[:, None] > Y[None, :]).astype(float) + 0.5 * (X[:, None] == Y[None, :])
        aucs.append(psi.mean())
        v10.append(psi.mean(axis=1))
        v01.append(psi.mean(axis=0))
    s10 = np.cov(np.vstack(v10))
    s01 = np.cov(np.vstack(v01))
    s = s10 / m + s01 / n
    var = s[0, 0] + s[1, 1] - 2 * s[0, 1]
    d = aucs[0] - aucs[1]
    z = d / np.sqrt(var) if var > 0 else 0.0
    out.update(auc_a=float(aucs[0]), auc_b=float(aucs[1]), diff=float(d),
               ci=[float(d - 1.959964 * np.sqrt(var)), float(d + 1.959964 * np.sqrt(var))],
               p=float(2 * stats.norm.sf(abs(z))))
    return out


def cell_tests(d: np.ndarray) -> dict[str, object]:
    idx = RNG.integers(0, len(d), size=(N_BOOT, len(d)))
    m = d[idx].mean(axis=1)
    pos, neg = int(np.sum(d > 1e-12)), int(np.sum(d < -1e-12))
    out = {"mean": float(d.mean()), "ci": [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))],
           "positive": pos, "zero": len(d) - pos - neg, "negative": neg,
           "p_t": float(stats.ttest_1samp(d, 0).pvalue)}
    try:
        out["p_wilcoxon"] = float(stats.wilcoxon(d).pvalue)
    except ValueError:
        out["p_wilcoxon"] = 1.0
    return out


def holm(p: list[float]) -> list[float]:
    p = np.asarray(p)
    order, adj, run = np.argsort(p), np.empty(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, (len(p) - r) * p[i])
        adj[i] = min(1.0, run)
    return adj.tolist()


# ----------------------------------------------------------------- loading
def load_preds(root: Path) -> dict[tuple[str, str, str], pd.DataFrame]:
    out = {}
    for f in root.glob("*/*.csv"):
        m = re.match(r"(.+)__(test|midrc|all)$", f.stem)
        if m:
            out[(f.parent.name, m.group(1), m.group(2))] = pd.read_csv(f, dtype={"patient_id": str})
    return out


def cell_of(name: str) -> tuple[int, int]:
    m = re.search(r"f(\d\d)_s(\d+)", name)
    return int(m.group(1)), int(m.group(2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True)
    ap.add_argument("--runs", default="src/records/runs510_per_run.csv")
    ap.add_argument("--sup128", default="src/records/sup128_per_run.csv")
    ap.add_argument("--out", default="src/records/derived/round3_prediction_analysis.json")
    args = ap.parse_args()
    P = load_preds(Path(args.preds))
    runs = pd.read_csv(args.runs, dtype={"tau": str, "lambda": str})
    sup = pd.read_csv(args.sup128)
    res: dict[str, object] = {}

    # ---------------- reproduce recorded test BA from predictions
    # Extension-B runs reuse the run names of initial-grid runs, so key by (group, run).
    group_of = {"stage_a": "stage_a", "jdcnet_initial": "bimcv_pseudolabel_cv_20260516",
                "jdcnet_extension_a": "bimcv_pseudolabel_lam15_20260516", "jdcnet_extension_b": "bimcv_pseudolabel_soft_20260516"}
    rec = {}
    for _, r in runs.iterrows():
        if r["stage"] in group_of:
            rec[(group_of[r["stage"]], r["run"])] = r["test_balanced_accuracy"]
    for _, r in sup.iterrows():
        rec[("sup128_restarts", r["run"])] = r["test_balanced_accuracy"]
    diffs = []
    mismatches = []
    for (g, name, kind), df in P.items():
        if kind == "test" and (g, name) in rec:
            d = abs(ba(df.label.values, df.prob_pos.values) - rec[(g, name)])
            diffs.append(d)
            if d > 1e-6:
                mismatches.append({"group": g, "run": name, "abs_ba_diff": float(d)})
    res["reproduction_max_abs_ba_diff"] = float(max(diffs)) if diffs else None
    res["reproduction_n"] = len(diffs)
    res["reproduction_n_exact"] = len(diffs) - len(mismatches)
    res["reproduction_mismatches"] = sorted(mismatches, key=lambda m: (m["group"], m["run"]))

    # ---------------- define methods: {cell: run name, group}
    cells = [(f, s) for f in range(5) for s in (42, 43, 44)]
    jd = runs[runs.stage.str.startswith("jdcnet")].copy()
    jd["config"] = jd["variant"] + "|" + jd["tau"] + "|" + jd["lambda"] + "|" + jd["target"]
    group_of_stage = {"jdcnet_initial": "bimcv_pseudolabel_cv_20260516", "jdcnet_extension_a": "bimcv_pseudolabel_lam15_20260516",
                      "jdcnet_extension_b": "bimcv_pseudolabel_soft_20260516"}
    jd["group"] = jd["stage"].map(group_of_stage)
    jd["cell"] = list(zip(jd["fold"].astype(int), jd["seed"].astype(int)))
    sup["cell"] = [cell_of(n) for n in sup["run"]]
    sup["r"] = sup["run"].str.extract(r"_r(\d\d)$")[0].astype(int)

    def pick(df, key="val_balanced_accuracy"):
        return {c: df[df.cell == c].sort_values(key, ascending=False).iloc[0] for c in cells}

    methods = {}
    methods["sup512"] = {c: ("stage_a", f"mid_f{c[0]:02d}_s{c[1]}_supervised") for c in cells}
    methods["sup128_r00"] = {c: ("sup128_restarts", f"sup128_f{c[0]:02d}_s{c[1]}_r00") for c in cells}
    best_sup = pick(sup)
    methods["sup128_best16_val"] = {c: ("sup128_restarts", best_sup[c]["run"]) for c in cells}
    best_sup8 = pick(sup[sup.r < 8])
    methods["sup128_best8_val"] = {c: ("sup128_restarts", best_sup8[c]["run"]) for c in cells}
    best_jd = pick(jd)
    methods["jdcnet_best16_val"] = {c: (best_jd[c]["group"], best_jd[c]["run"]) for c in cells}
    best_jd8 = pick(jd[jd.stage == "jdcnet_initial"])
    methods["jdcnet_best8_val"] = {c: (best_jd8[c]["group"], best_jd8[c]["run"]) for c in cells}
    for cfg in sorted(jd.config.unique()):
        sub = jd[jd.config == cfg]
        methods["jdcnet:" + cfg] = {c: (sub[sub.cell == c].iloc[0]["group"], sub[sub.cell == c].iloc[0]["run"]) for c in cells}

    def cell_vals(method, kind="test", fn=ba):
        return np.array([fn(P[(g, n, kind)].label.values, P[(g, n, kind)].prob_pos.values) for c in cells for g, n in [methods[method][c]]])

    # ---------------- cell-level comparisons
    comps = {}
    jd_cfgs = [m for m in methods if m.startswith("jdcnet:")]
    for base in ("sup512", "sup128_r00"):
        bvals = cell_vals(base)
        rows = {m: cell_tests(cell_vals(m) - bvals) for m in jd_cfgs}
        hol = holm([rows[m]["p_t"] for m in jd_cfgs])
        for m, h in zip(jd_cfgs, hol):
            rows[m]["p_t_holm"] = h
        comps[f"jdcnet_configs_vs_{base}"] = rows
    comps["sup128_r00_vs_sup512"] = cell_tests(cell_vals("sup128_r00") - cell_vals("sup512"))
    comps["nested16_jdcnet_vs_sup128_best16"] = cell_tests(cell_vals("jdcnet_best16_val") - cell_vals("sup128_best16_val"))
    comps["nested8_jdcnet_vs_sup128_best8"] = cell_tests(cell_vals("jdcnet_best8_val") - cell_vals("sup128_best8_val"))
    comps["nested16_jdcnet_vs_sup128_r00"] = cell_tests(cell_vals("jdcnet_best16_val") - cell_vals("sup128_r00"))
    comps["nested16_jdcnet_vs_sup512"] = cell_tests(cell_vals("jdcnet_best16_val") - cell_vals("sup512"))
    comps["sup128_best16_vs_sup128_r00"] = cell_tests(cell_vals("sup128_best16_val") - cell_vals("sup128_r00"))
    res["cell_level"] = comps
    res["absolute_test_ba"] = {m: float(cell_vals(m).mean()) for m in methods}
    res["absolute_test_auc"] = {m: float(cell_vals(m, fn=auc).mean()) for m in methods}

    # ---------------- patient-level paired bootstrap (out-of-fold, per seed)
    def oof(method):
        per_seed = {}
        for s in (42, 43, 44):
            parts = [P[methods[method][(f, s)][0], methods[method][(f, s)][1], "test"].assign(fold=f) for f in range(5)]
            per_seed[s] = pd.concat(parts).set_index("patient_id").sort_index()
        return per_seed

    def patient_boot(ma, mb):
        A, B = oof(ma), oof(mb)
        ids = A[42].index.values
        assert all((A[s].index.values == ids).all() and (B[s].index.values == ids).all() for s in (42, 43, 44))
        y = A[42].label.values
        pa = np.stack([A[s].prob_pos.values for s in (42, 43, 44)])
        pb = np.stack([B[s].prob_pos.values for s in (42, 43, 44)])
        def stat(idx):
            yy = y[idx]
            return np.mean([ba(yy, pa[k, idx]) - ba(yy, pb[k, idx]) for k in range(3)])
        obs = stat(np.arange(len(y)))
        boots = np.array([stat(RNG.integers(0, len(y), len(y))) for _ in range(N_BOOT)])
        return {"diff": float(obs), "ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                "p_two_sided": float(min(1.0, 2 * min(np.mean(boots <= 0), np.mean(boots >= 0)))),
                "n_patients": int(len(y))}
    pb = {}
    for ma, mb in [("jdcnet:3slice|0.70|1.0|soft_kl", "sup512"), ("jdcnet:mid|0.80|1.5|hard", "sup512"),
                   ("jdcnet:3slice|0.70|1.0|soft_kl", "sup128_r00"), ("jdcnet:mid|0.80|1.5|hard", "sup128_r00"),
                   ("sup128_r00", "sup512"), ("jdcnet_best16_val", "sup128_best16_val"), ("jdcnet_best16_val", "sup512")]:
        pb[f"{ma} - {mb}"] = patient_boot(ma, mb)
    res["patient_level_bootstrap"] = pb

    # ---------------- external MIDRC
    ext = {}
    def ext_scores(method):
        dfs = [P[(g, n, "midrc")] for c in cells for g, n in [methods[method][c]]]
        y = dfs[0].label.values
        probs = np.stack([d.prob_pos.values for d in dfs])
        return y, probs
    for m in ["sup512", "sup128_r00", "jdcnet:3slice|0.70|1.0|soft_kl", "jdcnet:mid|0.80|1.5|hard", "jdcnet_best16_val", "sup128_best16_val"]:
        y, probs = ext_scores(m)
        per_ckpt_ba = [ba(y, p) for p in probs]
        per_ckpt_auc = [auc(y, p) for p in probs]
        ens = probs.mean(axis=0)
        ext[m] = {"ba_mean": float(np.mean(per_ckpt_ba)), "ba_sd": float(np.std(per_ckpt_ba, ddof=1)),
                  "auc_mean": float(np.mean(per_ckpt_auc)), "auc_sd": float(np.std(per_ckpt_auc, ddof=1)),
                  "ensemble_ba": ba(y, ens), "ensemble_auc": auc(y, ens),
                  "mean_pred_positive_rate": float(np.mean(probs > 0.5))}
    for a_, b_ in [("jdcnet:3slice|0.70|1.0|soft_kl", "sup512"), ("jdcnet:mid|0.80|1.5|hard", "sup512"),
                   ("jdcnet:3slice|0.70|1.0|soft_kl", "sup128_r00"), ("jdcnet:mid|0.80|1.5|hard", "sup128_r00")]:
        y, pa_ = ext_scores(a_)
        _, pb_ = ext_scores(b_)
        ext[f"delong_ensemble {a_} - {b_}"] = delong(y, pa_.mean(axis=0), pb_.mean(axis=0))
        per_cell = [delong(y, pa_[k], pb_[k])["diff"] for k in range(len(cells))]
        ext[f"cellwise_auc_diff {a_} - {b_}"] = cell_tests(np.array(per_cell))
        per_cell_ba = [ba(y, pa_[k]) - ba(y, pb_[k]) for k in range(len(cells))]
        ext[f"cellwise_ba_diff {a_} - {b_}"] = cell_tests(np.array(per_cell_ba))
        # pre-specified McNemar-type comparison per checkpoint pair (exact binomial test on discordant images)
        mc = []
        for k in range(len(cells)):
            ca, cb = (pa_[k] > 0.5).astype(int) == y, (pb_[k] > 0.5).astype(int) == y
            n_a, n_b = int(np.sum(ca & ~cb)), int(np.sum(~ca & cb))
            p_mc = float(stats.binomtest(n_a, n_a + n_b, 0.5).pvalue) if n_a + n_b > 0 else 1.0
            mc.append({"a_only_correct": n_a, "b_only_correct": n_b, "p": p_mc})
        ps = np.array([m["p"] for m in mc])
        ext[f"mcnemar {a_} - {b_}"] = {"pairs": mc, "n_pairs": len(mc), "n_p_below_0.05": int(np.sum(ps < 0.05)),
                                       "median_p": float(np.median(ps)), "min_p": float(ps.min()),
                                       "mean_discordant": float(np.mean([m["a_only_correct"] + m["b_only_correct"] for m in mc])),
                                       "n_pairs_a_better": int(sum(m["a_only_correct"] > m["b_only_correct"] for m in mc)),
                                       "n_pairs_b_better": int(sum(m["a_only_correct"] < m["b_only_correct"] for m in mc))}
    res["external_midrc"] = ext

    # ---------------- teacher calibration
    teach = {}
    trows = [(n, df) for (g, n, k), df in P.items() if g == "teacher" and k == "all"]
    if trows:
        recs = []
        for n, df in trows:
            view = n.split("_f")[0]
            f_, s_ = cell_of(n)
            p = df.prob_pos.values.clip(1e-6, 1 - 1e-6)
            y = df.label.values
            conf = np.maximum(p, 1 - p)
            pred = (p > 0.5).astype(int)
            z = np.log(p / (1 - p))
            # temperature fitted on the validation partition by NLL
            v = (df.split == "val").values
            Ts = np.exp(np.linspace(np.log(0.25), np.log(8), 200))
            nll = [-np.mean(y[v] * np.log(1 / (1 + np.exp(-z[v] / T))) + (1 - y[v]) * np.log(1 - 1 / (1 + np.exp(-z[v] / T)))) for T in Ts]
            T_fit = float(Ts[int(np.argmin(nll))])
            for part in ("train", "val", "test"):
                mk = (df.split == part).values
                row = {"view": view, "fold": f_, "seed": s_, "part": part, "n": int(mk.sum()),
                       "acc": float(np.mean(pred[mk] == y[mk])), "ba": ba(y[mk], p[mk]),
                       "ece": ece(conf[mk], pred[mk] == y[mk]), "T_fit": T_fit,
                       "ece_after_T": ece(np.maximum(1 / (1 + np.exp(-z[mk] / T_fit)), 1 - 1 / (1 + np.exp(-z[mk] / T_fit))), pred[mk] == y[mk])}
                for tau in (0.60, 0.70, 0.80, 0.85):
                    keep = conf[mk] > tau
                    row[f"cov_{tau:.2f}"] = float(keep.mean())
                    row[f"cov_pos_{tau:.2f}"] = float(keep[y[mk] == 1].mean())
                    row[f"cov_neg_{tau:.2f}"] = float(keep[y[mk] == 0].mean())
                    corr = (pred[mk] == y[mk])
                    row[f"acc_kept_{tau:.2f}"] = float(corr[keep].mean()) if keep.any() else float("nan")
                    row[f"acc_rej_{tau:.2f}"] = float(corr[~keep].mean()) if (~keep).any() else float("nan")
                recs.append(row)
        tdf = pd.DataFrame(recs)
        teach["by_view_part"] = tdf.groupby(["view", "part"]).mean(numeric_only=True).reset_index().to_dict(orient="records")
        # reproduction of recorded teacher test BA
        rt = runs[(runs.stage == "stage_a") & (runs.method == "teacher")].set_index("run")["test_balanced_accuracy"]
        diffs = []
        for n, df in trows:
            if n in rt.index:
                mk = (df.split == "test").values
                diffs.append(abs(ba(df.label.values[mk], df.prob_pos.values[mk]) - rt[n]))
        teach["reproduction_max_abs_ba_diff"] = float(max(diffs)) if diffs else None
    res["teacher"] = teach

    # ---------------- pre-specified analysis 3 for analysis 1: patient-level bootstrap of every
    # configuration against the batch-matched baseline (run last so earlier RNG draws are unchanged)
    # comparisons already bootstrapped above are reused so each comparison has a single reported interval
    pb16 = {m: dict(pb[f"{m} - sup128_r00"]) if f"{m} - sup128_r00" in pb else patient_boot(m, "sup128_r00") for m in jd_cfgs}
    for m, h in zip(jd_cfgs, holm([pb16[m]["p_two_sided"] for m in jd_cfgs])):
        pb16[m]["p_holm"] = h
    res["patient_level_bootstrap_all16_vs_sup128_r00"] = pb16

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("reproduction_max_abs_ba_diff", "reproduction_n")}, indent=1))
    print("absolute test BA:", {k: round(v, 4) for k, v in res["absolute_test_ba"].items() if not k.startswith("jdcnet:")})
    for k, v in comps.items():
        if isinstance(v, dict) and "mean" in v:
            print(f"{k:40s} {v['mean']:+.4f} [{v['ci'][0]:+.4f},{v['ci'][1]:+.4f}] {v['positive']}/{v['zero']}/{v['negative']} pt={v['p_t']:.4f} pw={v['p_wilcoxon']:.4f}")
    for base in ("sup512", "sup128_r00"):
        print("\nJDCNet configs vs", base)
        for m, v in sorted(comps[f"jdcnet_configs_vs_{base}"].items(), key=lambda kv: -kv[1]["mean"]):
            print(f"  {m:34s} {v['mean']:+.4f} [{v['ci'][0]:+.4f},{v['ci'][1]:+.4f}] {v['positive']}/{v['zero']}/{v['negative']} pt={v['p_t']:.4f} holm={v['p_t_holm']:.3f}")
    print("\npatient-level:")
    for k, v in pb.items():
        print(f"  {k:60s} {v['diff']:+.4f} [{v['ci'][0]:+.4f},{v['ci'][1]:+.4f}] p={v['p_two_sided']:.4f}")
    print("\nexternal:")
    for k, v in ext.items():
        print(" ", k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    if teach:
        print("\nteacher reproduction max diff:", teach.get("reproduction_max_abs_ba_diff"))
        for r in teach["by_view_part"]:
            print("  ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("fold", "seed")})


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 15) -> float:
    edges = np.linspace(0.5, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0.5 else (conf >= lo) & (conf <= hi)
        if m.any():
            total += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(total)


if __name__ == "__main__":
    main()
