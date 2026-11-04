"""Evaluate externally trained models on the cohort against caliper-derived weak lesion boxes."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import timm
import torch

from thyroid_exp.train_external import UNet, to_tensor


def reference_region(row) -> tuple[float, float, float, float, bool]:
    """Return the reference box, widening one-axis measurements, and whether the box is truly 2D."""
    x0, y0, x1, y1 = row.box_x0, row.box_y0, row.box_x1, row.box_y1
    bw, bh = x1 - x0, y1 - y0
    long_side, short_side = max(bw, bh), min(bw, bh)
    is_2d = short_side >= 0.30 * long_side
    if short_side < 0.60 * long_side:
        pad = (0.60 * long_side - short_side) / 2
        if bw < bh:
            x0, x1 = x0 - pad, x1 + pad
        else:
            y0, y1 = y0 - pad, y1 + pad
    return x0, y0, x1, y1, is_2d


def box_iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def largest_component(prob: np.ndarray) -> tuple | None:
    mask = (prob > 0.5).astype(np.uint8)
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = stats[i]
    return (float(x), float(y), float(x + w), float(y + h)), (float(cents[i][0]), float(cents[i][1])), int(area)


def bootstrap_ci(frame: pd.DataFrame, stat, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Patient-level bootstrap, since images from one patient are not independent."""
    groups = {k: v for k, v in frame.groupby("patient")}
    keys = np.array(list(groups))
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        sample = pd.concat([groups[k] for k in rng.choice(keys, len(keys))], ignore_index=True)
        vals.append(stat(sample))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def lesion_removed(img: np.ndarray, box: tuple) -> np.ndarray:
    """Occlusion control: replace the weak lesion box with inpainted surrounding tissue."""
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    mask[max(0, y0 - 3):min(h, y1 + 4), max(0, x0 - 3):min(w, x1 + 4)] = 1
    small = cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    small_mask = cv2.resize(mask, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST)
    filled = cv2.resize(cv2.inpaint(small, small_mask, 5, cv2.INPAINT_TELEA), (w, h), interpolation=cv2.INTER_LINEAR)
    out = img.copy()
    out[mask > 0] = filled[mask > 0]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--cache-dir", type=Path, required=True)
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, default=320)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    seg = UNet().to(device)
    seg.load_state_dict(torch.load(args.models / "seg.pt", map_location=device))
    seg.eval()
    clf = timm.create_model("resnet34", pretrained=False, num_classes=1).to(device)
    clf.load_state_dict(torch.load(args.models / "clf.pt", map_location=device))
    clf.eval()
    ext = json.loads((args.models / "external_summary.json").read_text())

    df = pd.read_csv(args.manifest)
    use = df[df.usable == 1].copy()

    # Centre prior: normalised mean centre and median size, a baseline that already knows the cohort.
    nx = ((use.box_x0 + use.box_x1) / 2 / use.sector_w).mean()
    ny = ((use.box_y0 + use.box_y1) / 2 / use.sector_h).mean()
    nw = ((use.box_x1 - use.box_x0) / use.sector_w).median()
    nh = ((use.box_y1 - use.box_y0) / use.sector_h).median()

    rows = []
    with torch.no_grad():
        for r in use.itertuples():
            ref = reference_region(r)
            box = ref[:4]
            rec = dict(image_uid=r.image_uid, patient=r.patient, scanner=r.scanner, source=r.source, is_2d=ref[4])
            w, h = r.sector_w, r.sector_h
            imgs = {cond: cv2.imread(str(args.cache_dir / cond / f"{r.image_uid}.png")) for cond in ("raw", "erased")}
            imgs["lesion_removed"] = lesion_removed(imgs["erased"], (r.box_x0, r.box_y0, r.box_x1, r.box_y1))
            for cond, img in imgs.items():
                x = to_tensor(img, args.size)[None].to(device)
                rec[f"p_malig_{cond}"] = float(torch.sigmoid(clf(x)).item())
                if cond == "lesion_removed":
                    continue
                prob = cv2.resize(torch.sigmoid(seg(x))[0, 0].cpu().numpy(), (w, h), interpolation=cv2.INTER_LINEAR)
                comp = largest_component(prob)
                if comp is None:
                    rec.update({f"hit_{cond}": 0, f"iou_{cond}": 0.0, f"axis_err_{cond}": np.nan})
                else:
                    pb, (cx, cy), _ = comp
                    rec[f"hit_{cond}"] = int(box[0] <= cx <= box[2] and box[1] <= cy <= box[3])
                    rec[f"iou_{cond}"] = box_iou(pb, (r.box_x0, r.box_y0, r.box_x1, r.box_y1))
                    ref_axis = max(r.box_x1 - r.box_x0, r.box_y1 - r.box_y0)
                    rec[f"axis_err_{cond}"] = abs(max(pb[2] - pb[0], pb[3] - pb[1]) - ref_axis) / max(ref_axis, 1.0)
            cx, cy = nx * w, ny * h
            pw, ph = nw * w, nh * h
            rec["hit_prior"] = int(box[0] <= cx <= box[2] and box[1] <= cy <= box[3])
            rec["iou_prior"] = box_iou((cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2),
                                       (r.box_x0, r.box_y0, r.box_x1, r.box_y1))
            rows.append(rec)
    res = pd.DataFrame(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    res.to_csv(args.out / "per_image.csv", index=False)

    two_d = res[res.is_2d]
    gain = lambda s: s.hit_erased.mean() - s.hit_prior.mean()
    reliance = lambda s: s.hit_raw.mean() - s.hit_erased.mean()
    summary = dict(
        n_images_total=int(len(df)), n_images_usable=int(len(use)), usable_rate=float(len(use) / len(df)),
        n_patients_usable=int(use.patient.nunique()), n_2d_boxes=int(len(two_d)),
        hit_erased=float(res.hit_erased.mean()), hit_raw=float(res.hit_raw.mean()), hit_prior=float(res.hit_prior.mean()),
        iou_erased_median_2d=float(two_d.iou_erased.median()), iou_raw_median_2d=float(two_d.iou_raw.median()),
        iou_prior_median_2d=float(two_d.iou_prior.median()),
        axis_err_erased_median=float(res.axis_err_erased.median()),
        hit_gain=float(gain(res)), hit_gain_ci=bootstrap_ci(res, gain),
        hit_erased_ci=bootstrap_ci(res, lambda s: s.hit_erased.mean()),
        caliper_reliance=float(reliance(res)), caliper_reliance_ci=bootstrap_ci(res, reliance),
    )
    per_scanner = res.groupby("scanner").agg(
        n=("hit_erased", "size"), patients=("patient", "nunique"), hit_erased=("hit_erased", "mean"),
        hit_raw=("hit_raw", "mean"), hit_prior=("hit_prior", "mean"), iou_erased=("iou_erased", "median"),
    ).sort_values("n", ascending=False)
    per_scanner.to_csv(args.out / "per_scanner.csv")
    per_source = res.groupby("source").agg(n=("hit_erased", "size"), hit_erased=("hit_erased", "mean"), hit_prior=("hit_prior", "mean"))
    per_source.to_csv(args.out / "per_source.csv")

    # Descriptive sensitivity. The batch has no benign cases, so no specificity can be stated here.
    clf_rows = []
    for name, thr in (("spec80_on_public_val", ext["thr_spec80"]), ("sens90_on_public_val", ext["thr_sens90"])):
        for cond in ("raw", "erased", "lesion_removed"):
            col = f"p_malig_{cond}"
            rate = lambda s, c=col, t=thr: (s[c] >= t).mean()
            lo, hi = bootstrap_ci(res, rate)
            clf_rows.append(dict(operating_point=name, threshold=thr, condition=cond, call_rate=float(rate(res)), ci_low=lo, ci_high=hi))
    clf_df = pd.DataFrame(clf_rows)
    clf_df.to_csv(args.out / "classifier_call_rates.csv", index=False)
    summary["classifier_median_p"] = {c: float(res[f"p_malig_{c}"].median()) for c in ("raw", "erased", "lesion_removed")}

    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(per_scanner.round(3).to_string())
    print(per_source.round(3).to_string())
    print(clf_df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
