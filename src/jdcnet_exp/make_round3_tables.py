"""Generate LaTeX table rows for the round-3 manuscript from the derived JSON records.

Usage:
    python -m jdcnet_exp.make_round3_tables > records/derived/round3_tables.tex
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "records" / "derived"
full = json.loads((D / "round3_full_analysis.json").read_text())
rest = json.loads((D / "round3_restart_analysis.json").read_text())
pred = json.loads((D / "round3_prediction_analysis.json").read_text())
grid = pd.read_csv(ROOT / "records" / "jdcnet510_grid_summary.csv", dtype={"tau": str})
sup128 = pd.read_csv(ROOT / "records" / "sup128_per_run.csv")


def s(x, d=4):
    return f"${'+' if x >= 0 else '-'}{abs(x):.{d}f}$"


def p(x):
    if x < 0.001:
        return "$<0.001$"
    return f"{x:.3f}" if x < 0.1 else f"{x:.2f}"


STAGE = {"initial": "I", "extension_a": "A", "extension_b": "B"}
TGT = {"hard": "hard", "soft_kl": "soft-KL"}

print("% ---- Table 4: 16 JDCNet configurations")
rows = []
for _, g in grid.iterrows():
    key = f"{g.teacher}|{float(g.tau):.2f}|{float(g['lambda']):.1f}|{g.target}"
    r = full["jdcnet"][key]["delta"]
    rm = rest["vs_sup128_restart_mean"][key]
    rows.append((g.delta_ba_mean, g, r, rm))
for mean, g, r, rm in sorted(rows, key=lambda t: -t[0]):
    view = "3-slice" if g.teacher == "3slice" else "Mid"
    rule = "Yes" if (g.delta_ba_mean >= 0.03 and g.delta_ba_ci_lo > 0) else "--"
    print(f"{view} & {float(g.tau):.2f} & {float(g['lambda']):.1f} & {TGT[g.target]} & {STAGE[g.stage]} & "
          f"{g.positive}/{g.zero}/{g.negative} & {s(g.delta_ba_mean)} & [{s(g.delta_ba_ci_lo)}, {s(g.delta_ba_ci_hi)}] & "
          f"{p(r['p_t'])} & {p(r['p_t_holm'])} & {s(rm['mean'], 3)} & {rule} \\\\")

print("\n% ---- Table 5: absolute metrics")
def absrow(label, a):
    print(f"{label} & ${a['ba']:.3f}\\,({a['ba_sd']:.3f})$ & ${a['auc']:.3f}\\,({a['auc_sd']:.3f})$ & ${a['macro_f1']:.3f}$ & "
          f"${a['sens']:.3f}\\,({a['sens_sd']:.3f})$ & ${a['spec']:.3f}\\,({a['spec_sd']:.3f})$ \\\\")
absrow("Supervised X-ray, batch 512", full["supervised"])
r0 = sup128[sup128.r == 0]
absrow("Supervised X-ray, batch 128 ($r{=}0$)", {"ba": r0.test_balanced_accuracy.mean(), "ba_sd": r0.test_balanced_accuracy.std(),
       "auc": r0.test_roc_auc.mean(), "auc_sd": r0.test_roc_auc.std(), "macro_f1": r0.test_macro_f1.mean(),
       "sens": r0.test_recall.mean(), "sens_sd": r0.test_recall.std(), "spec": r0.test_specificity.mean(), "spec_sd": r0.test_specificity.std()})
absrow("JDCNet 3-slice soft-KL", full["jdcnet"]["3slice|0.70|1.0|soft_kl"]["absolute"])
absrow("JDCNet mid hard", full["jdcnet"]["mid|0.80|1.5|hard"]["absolute"])
for key, label in [("stage_a/mid/plain_kd", "Plain logit KD, mid"), ("stage_a/mid/gated_kd_thr050", "Gated logit KD, mid"),
                   ("stage_a/drr/gated_kd_thr050", "Gated logit KD, DRR"), ("stage_a/mid/teacher", "CT-only reference, mid"),
                   ("stage_a/3slice/teacher", "CT-only reference, 3-slice")]:
    absrow(label, full["stage_a"][key]["absolute"])
absrow("Contrastive alignment, best", full["contrastive"]["3slice/contrastive_t020"])

print("\n% ---- Stage A deltas")
for key, v in full["stage_a"].items():
    if key.endswith("supervised"):
        continue
    t = v["delta"]
    print(f"% {key}: {s(t['mean'],3)} [{s(t['ci'][0],3)}, {s(t['ci'][1],3)}] {t['positive']}/{t['zero']}/{t['negative']} p_t={p(t['p_t'])}")
for key, t in full["contrastive_delta"].items():
    print(f"% contrastive {key}: {s(t['mean'],3)} [{s(t['ci'][0],3)}, {s(t['ci'][1],3)}] {t['positive']}/{t['zero']}/{t['negative']} p_t={p(t['p_t'])}")

print("\n% ---- External MIDRC (126 images)")
ext = pred["external_midrc"]
def wilson(pp, n=126, z=1.959964):
    den = 1 + z * z / n
    c = (pp + z * z / (2 * n)) / den
    h = z * math.sqrt(pp * (1 - pp) / n + z * z / (4 * n * n)) / den
    return c - h, c + h
def hm(a, n1=63, n2=63):
    q1, q2 = a / (2 - a), 2 * a * a / (1 + a)
    se = math.sqrt((a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n2 - 1) * (q2 - a * a)) / (n1 * n2))
    return a - 1.959964 * se, a + 1.959964 * se
for key, label in [("sup512", "Supervised, batch 512"), ("sup128_r00", "Supervised, batch 128"),
                   ("jdcnet:3slice|0.70|1.0|soft_kl", "JDCNet 3-slice soft-KL"), ("jdcnet:mid|0.80|1.5|hard", "JDCNet mid hard")]:
    e = ext[key]
    lo, hi = wilson(e["ba_mean"]); alo, ahi = hm(e["auc_mean"])
    print(f"{label} (15) & {e['ba_mean']:.3f} [{lo:.3f}, {hi:.3f}] & {e['auc_mean']:.3f} [{alo:.3f}, {ahi:.3f}] & {e['ensemble_auc']:.3f} & {e['mean_pred_positive_rate']:.2f} \\\\")
for k, v in ext.items():
    if k.startswith("delong") or k.startswith("cellwise"):
        if "diff" in v:
            print(f"% {k}: diff {v['diff']:+.3f} CI [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] p={v['p']:.2f}")
        else:
            print(f"% {k}: mean {v['mean']:+.3f} CI [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] p_t={v['p_t']:.2f}")

print("\n% ---- Teacher reliability")
tv = pd.DataFrame(pred["teacher"]["by_view_part"])
for view in ("mid", "3slice", "proj", "drr"):
    for part in ("train", "val", "test"):
        r = tv[(tv.view == view) & (tv.part == part)].iloc[0]
        name = {"mid": "Mid-slice", "3slice": "3-slice", "proj": "Mean proj.", "drr": "DRR"}[view]
        print(f"{name if part == 'train' else ''} & {part} & {r.acc:.3f} & {r.ece:.3f} & {r['cov_0.70']:.2f} & {r['cov_0.80']:.2f} & "
              f"{r['acc_kept_0.80']:.3f} / {r['acc_rej_0.80']:.3f} & {r.T_fit:.2f} \\\\")
