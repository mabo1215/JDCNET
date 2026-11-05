"""Build a single-file offline annotation page from a device-stratified image sample.

The page embeds sector crops under pseudonyms, with burned-in text blacked out, and box coordinates
are in the same sector coordinates as the manifest. Calipers stay visible because the annotator needs
them to identify the measured nodule. One image is taken per patient.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from thyroid_exp.extract_calipers import sector_box

ALLOCATION = {
    "mindray": 14, "canon_aplio": 14, "philips": 14, "xr80a": 10, "ultimus": 8, "siemens_sequoia": 6, "ge_logiq": 8,
    "ui_dist_ab": 5, "siemens_s": 3, "ui_qscan": 2, "esaote_mylab": 2, "toshiba_xario": 1, "unidentified": 13,
}


def sample_images(manifest: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Draw per-device quotas with no patient repeated, then top up from the unidentified group."""
    eligible = manifest[(manifest.source != "doppler") & (manifest.sector_w >= 150) & (manifest.sector_h >= 150)]
    eligible = eligible.sample(frac=1.0, random_state=seed)
    chosen, seen = [], set()
    for group, quota in ALLOCATION.items():
        taken = 0
        for row in eligible[eligible.scanner == group].itertuples():
            if taken == quota:
                break
            if row.patient not in seen:
                seen.add(row.patient)
                chosen.append(row.image_uid)
                taken += 1
    shortfall = sum(ALLOCATION.values()) - len(chosen)
    if shortfall:
        extra = [r for r in eligible.itertuples() if r.patient not in seen]
        for row in extra:
            if shortfall == 0:
                break
            if row.patient not in seen:
                seen.add(row.patient)
                chosen.append(row.image_uid)
                shortfall -= 1
    picked = eligible[eligible.image_uid.isin(chosen)]
    return picked.sample(frac=1.0, random_state=seed + 1)  # shuffled so devices are not reviewed in blocks


def render_crop(path: Path, ocr_items: list, expected: tuple[int, int], quality: int) -> tuple[str, int, int]:
    """Reproduce the manifest crop, black out burned-in text and return a JPEG data URI."""
    im = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    full_text = np.zeros(gray.shape, np.uint8)
    for box, _ in ocr_items:
        cv2.fillPoly(full_text, [np.asarray(box, np.int32)], 1)
    full_text = cv2.dilate(full_text, np.ones((5, 5), np.uint8))
    x0, y0, x1, y1 = sector_box(gray, full_text)
    sector = im[y0:y1, x0:x1].copy()
    h, w = sector.shape[:2]
    if (w, h) != expected:
        raise ValueError("crop does not match the manifest")
    # Single characters are usually caliper labels, which the annotator needs. Longer text is hidden.
    for box, text in ocr_items:
        if len(str(text).strip()) >= 2:
            poly = np.asarray(box, np.int32) - np.array([x0, y0])
            cv2.fillPoly(sector, [poly], (0, 0, 0))
    ok, buf = cv2.imencode(".jpg", sector, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG encoding failed")
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii"), w, h


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--raw-root", type=Path, required=True)
    ap.add_argument("--key-file", type=Path, required=True)
    ap.add_argument("--ocr-cache", type=Path, required=True)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sample-list", type=Path, required=True, help="Sampled pseudonyms and device groups")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--quality", type=int, default=92)
    args = ap.parse_args()

    manifest = pd.read_csv(args.manifest)
    picked = sample_images(manifest, args.seed)
    with args.key_file.open(newline="", encoding="utf-8") as fh:
        folders = {row["patient"]: row["source_folder"] for row in csv.DictReader(fh)}
    cache = json.loads(args.ocr_cache.read_text(encoding="utf-8"))

    pack = []
    for row in picked.itertuples():
        index = int(row.image_uid.split("_")[1])
        folder = args.raw_root / folders[row.patient]
        files = sorted(f for f in folder.iterdir() if f.suffix.lower() in {".jpg", ".jpeg"})
        src, w, h = render_crop(files[index - 1], cache[row.image_uid], (row.sector_w, row.sector_h), args.quality)
        pack.append(dict(uid=row.image_uid, w=w, h=h, src=src))

    html = args.template.read_text(encoding="utf-8")
    marker = "/*__PACK__*/[]"
    if html.count(marker) != 1:
        raise ValueError("template marker not found")
    args.out.write_text(html.replace(marker, json.dumps(pack)), encoding="utf-8", newline="\n")
    picked[["image_uid", "patient", "scanner", "source", "usable"]].to_csv(args.sample_list, index=False)

    print(f"images={len(pack)} patients={picked.patient.nunique()} size_mb={args.out.stat().st_size / 1e6:.1f}")
    print(picked.groupby("scanner").size().sort_values(ascending=False).to_string())
    print("already has an automatic box:", int(picked.usable.sum()))


if __name__ == "__main__":
    main()
