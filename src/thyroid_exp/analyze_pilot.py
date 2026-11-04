"""Negative control, paired classifier contrasts, gate verdicts and a prediction montage for the pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch

from thyroid_exp.evaluate_pilot import box_iou, largest_component, lesion_removed, reference_region
from thyroid_exp.train_external import UNet, to_tensor


def patient_bootstrap(frame: pd.DataFrame, values: np.ndarray, n: int = 5000, seed: int = 0) -> tuple[float, float, float]:
    """Return the image-weighted mean and a patient-level bootstrap 95% CI."""
    codes, _ = pd.factorize(frame.patient)
    sums = np.bincount(codes, weights=values)
    counts = np.bincount(codes)
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(len(sums), np.full(len(sums), 1 / len(sums)), size=n)
    means = (draws @ sums) / (draws @ counts)
    return float(values.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def fmt(triple: tuple[float, float, float], scale: float = 100.0) -> str:
    return f"{triple[0] * scale:+.1f} [{triple[1] * scale:+.1f}, {triple[2] * scale:+.1f}]"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--cache-dir", type=Path, required=True)
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--montage", type=Path, required=True)
    ap.add_argument("--size", type=int, default=320)
    ap.add_argument("--qc-full", type=int, required=True, help="Sampled overlays fully correct")
    ap.add_argument("--qc-partial", type=int, required=True, help="Sampled overlays on a true measurement, one axis only")
    ap.add_argument("--qc-wrong", type=int, required=True, help="Sampled overlays wrong")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    seg = UNet().to(device)
    seg.load_state_dict(torch.load(args.models / "seg.pt", map_location=device))
    seg.eval()
    ext = json.loads((args.models / "external_summary.json").read_text())
    manifest = pd.read_csv(args.results / "manifest.csv")
    use = manifest[manifest.usable == 1].reset_index(drop=True)
    res = pd.read_csv(args.results / "per_image.csv")
    res = res.merge(use[["image_uid", "box_x0", "box_y0", "box_x1", "box_y1", "sector_w", "sector_h"]], on="image_uid")

    # Negative control: with the lesion replaced by surrounding tissue, the hit rate should collapse.
    hits, ious, tiles = [], [], []
    picks = set(res.sample(n=min(24, len(res)), random_state=3).image_uid)
    with torch.no_grad():
        for r in res.itertuples():
            erased = cv2.imread(str(args.cache_dir / "erased" / f"{r.image_uid}.png"))
            box = (r.box_x0, r.box_y0, r.box_x1, r.box_y1)
            ref = reference_region(r)[:4]
            removed = lesion_removed(erased, box)
            x = to_tensor(removed, args.size)[None].to(device)
            prob = cv2.resize(torch.sigmoid(seg(x))[0, 0].cpu().numpy(), (r.sector_w, r.sector_h))
            comp = largest_component(prob)
            hits.append(0 if comp is None else int(ref[0] <= comp[1][0] <= ref[2] and ref[1] <= comp[1][1] <= ref[3]))
            ious.append(0.0 if comp is None else box_iou(comp[0], box))
            if r.image_uid in picks:
                x = to_tensor(erased, args.size)[None].to(device)
                prob = cv2.resize(torch.sigmoid(seg(x))[0, 0].cpu().numpy(), (r.sector_w, r.sector_h))
                view = erased.copy()
                contours, _ = cv2.findContours((prob > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(view, contours, -1, (0, 255, 0), 1)
                cv2.rectangle(view, (int(ref[0]), int(ref[1])), (int(ref[2]), int(ref[3])), (0, 255, 255), 1)
                tiles.append(cv2.resize(view, (320, 240), interpolation=cv2.INTER_AREA))
    res["hit_lesion_removed"] = hits
    res["iou_lesion_removed"] = ious
    rows = [np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles) - len(tiles) % 6, 6)]
    cv2.imwrite(str(args.montage), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])

    two_d = res[res.is_2d]
    hit_e = patient_bootstrap(res, res.hit_erased.to_numpy(float))
    hit_p = patient_bootstrap(res, res.hit_prior.to_numpy(float))
    hit_r = patient_bootstrap(res, res.hit_raw.to_numpy(float))
    hit_c = patient_bootstrap(res, res.hit_lesion_removed.to_numpy(float))
    gain = patient_bootstrap(res, (res.hit_erased - res.hit_prior).to_numpy(float))
    reliance = patient_bootstrap(res, (res.hit_raw - res.hit_erased).to_numpy(float))
    control = patient_bootstrap(res, (res.hit_erased - res.hit_lesion_removed).to_numpy(float))
    iou_e, iou_r, iou_p = two_d.iou_erased.median(), two_d.iou_raw.median(), two_d.iou_prior.median()

    scanners = []
    for name, g in res.groupby("scanner"):
        g2 = g[g.is_2d]
        scanners.append(dict(scanner=name, images=len(g), patients=g.patient.nunique(), hit_erased=g.hit_erased.mean(),
                             hit_prior=g.hit_prior.mean(), boxes_2d=len(g2),
                             iou_2d=g2.iou_erased.median() if len(g2) else float("nan")))
    per_scanner = pd.DataFrame(scanners).sort_values("images", ascending=False)
    per_scanner.to_csv(args.results / "per_scanner.csv", index=False)
    big = per_scanner[per_scanner.images >= 30]

    contrasts = []
    for name, thr in (("spec80_on_public_val", ext["thr_spec80"]), ("sens90_on_public_val", ext["thr_sens90"])):
        calls = {c: (res[f"p_malig_{c}"] >= thr).to_numpy(float) for c in ("raw", "erased", "lesion_removed")}
        contrasts.append(dict(
            operating_point=name,
            public_test_sensitivity=ext["test_sens_at_spec80" if "spec80" in name else "test_sens_at_sens90"],
            public_test_specificity=ext["test_spec_at_spec80" if "spec80" in name else "test_spec_at_sens90"],
            call_rate_erased=calls["erased"].mean(), call_rate_raw=calls["raw"].mean(),
            call_rate_lesion_removed=calls["lesion_removed"].mean(),
            erased_minus_removed=fmt(patient_bootstrap(res, calls["erased"] - calls["lesion_removed"])),
            erased_minus_raw=fmt(patient_bootstrap(res, calls["erased"] - calls["raw"])),
        ))
    contrast_df = pd.DataFrame(contrasts)
    contrast_df.to_csv(args.results / "classifier_contrasts.csv", index=False)

    n_qc = args.qc_full + args.qc_partial + args.qc_wrong
    usable_rate = len(use) / len(manifest)
    g1_cov = usable_rate >= 0.60
    g1_prec = n_qc >= 50 and args.qc_full / n_qc >= 0.80
    g2 = hit_e[0] >= 0.70 and iou_e >= 0.40 and gain[0] >= 0.15 and gain[1] > 0
    g3 = len(big) > 0 and (big.hit_erased >= 0.60).mean() >= 0.75
    g4 = reliance[0] <= 0.10

    report = [
        "# Pilot decision report",
        "",
        f"Cohort: {manifest.patient.nunique()} patients, {len(manifest)} images. Usable weak boxes: {len(use)} images "
        f"from {use.patient.nunique()} patients. Overlay review was done by an AI model, not a clinician.",
        "",
        "| Gate | Result | Threshold | Status |",
        "|---|---|---|---|",
        f"| G1 coverage | {usable_rate:.1%} of images | >= 60% | {'PASS' if g1_cov else 'FAIL'} |",
        f"| G1 overlay accuracy | {args.qc_full}/{n_qc} fully correct, {args.qc_partial} one axis only, {args.qc_wrong} wrong | >= 80% fully correct | {'PASS' if g1_prec else 'FAIL'} |",
        f"| G2 hit on erased images | {hit_e[0]:.1%} [{hit_e[1]:.1%}, {hit_e[2]:.1%}] | >= 70% | {'PASS' if hit_e[0] >= 0.70 else 'FAIL'} |",
        f"| G2 median box IoU, 2D boxes | {iou_e:.2f} (centre prior {iou_p:.2f}) | >= 0.40 | {'PASS' if iou_e >= 0.40 else 'FAIL'} |",
        f"| G2 hit gain over centre prior | {fmt(gain)} points | >= +15, CI excludes 0 | {'PASS' if gain[0] >= 0.15 and gain[1] > 0 else 'FAIL'} |",
        f"| G3 series with >= 30 images at hit >= 60% | {int((big.hit_erased >= 0.60).sum())}/{len(big)} series | >= 75% of series | {'PASS' if g3 else 'FAIL'} (only {len(big)} series testable) |",
        f"| G4 raw minus erased hit | {fmt(reliance)} points | <= +10 | {'PASS' if g4 else 'FAIL'} |",
        "",
        f"Verdict under the pre-specified rule: {'GO' if g1_cov and g1_prec and g2 and g3 and g4 else 'NOT GO'}.",
        "",
        "## Localisation detail",
        "",
        f"- Hit rate: erased {hit_e[0]:.1%}, raw {hit_r[0]:.1%}, centre prior {hit_p[0]:.1%}.",
        f"- Median box IoU on 2D boxes: erased {iou_e:.2f}, raw {iou_r:.2f}, centre prior {iou_p:.2f}.",
        f"- Negative control, lesion replaced by surrounding tissue: hit {hit_c[0]:.1%}, "
        f"median IoU {two_d.iou_lesion_removed.median():.2f}. Erased minus control: {fmt(control)} points.",
        "",
        per_scanner.round(3).to_markdown(index=False),
        "",
        "## Classifier, descriptive only",
        "",
        "This batch has no benign cases, so call rates are not diagnostic performance. Public labels come from "
        "radiologists according to the dataset description.",
        "",
        contrast_df.round(3).to_markdown(index=False),
        "",
    ]
    (args.results / "decision_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
