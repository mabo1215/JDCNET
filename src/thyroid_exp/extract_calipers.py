"""Build a pseudonymized manifest and caliper-derived weak lesion boxes.

For each thyroid ultrasound image this script:
  1. reads burned-in text locally, to mask it and to infer the scanner series,
  2. crops the imaging sector from local texture,
  3. rejects colour Doppler frames, whose flow signal would be mistaken for marks,
  4. detects caliper endpoints from coloured marks, or from achromatic cross templates,
  5. derives a weak lesion box from the main cluster of endpoints,
  6. writes a caliper-erased copy of the sector for model input.

Raw identifiers and raw OCR text are never written to the results directory. The pseudonym key and
the OCR cache are kept in a private, git-ignored directory.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import DBSCAN

SCANNER_RULES = [
    ("philips", r"philips|epiq|affiniti|iu22|ie33|hd11|hd15"),
    ("ge_logiq", r"logiq|voluson|\bs8\b"),
    ("mindray", r"mindray|resona|\bdc-?[0-9]{1,2}\b"),
    ("canon_aplio", r"aplio|canon"),
    ("xr80a", r"xr-?80"),
    ("siemens_sequoia", r"sequoia"),
    ("siemens_s", r"siemens|\bs[123]000\b|juniper|acuson"),
    ("ultimus", r"ultimus"),
    ("hisense", "hisense|\u6d77\u4fe1"),
    ("toshiba_xario", r"xario|toshiba"),
    ("esaote_mylab", r"mylab|esaote"),
]


def infer_scanner(text: str) -> str:
    low = text.lower()
    for name, pattern in SCANNER_RULES:
        if re.search(pattern, low):
            return name
    return "unidentified"


def sector_box(gray: np.ndarray, text_mask: np.ndarray) -> tuple[int, int, int, int]:
    """Return x0, y0, x1, y1 of the largest textured region, ignoring flat panels and text."""
    g = gray.astype(np.float32)
    mean = cv2.blur(g, (11, 11))
    std = np.sqrt(np.maximum(cv2.blur(g * g, (11, 11)) - mean * mean, 0))
    tex = ((std > 5) & (mean > 12)).astype(np.uint8)
    tex[text_mask > 0] = 0
    tex = cv2.morphologyEx(tex, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    tex = cv2.morphologyEx(tex, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    tex = cv2.morphologyEx(tex, cv2.MORPH_OPEN, np.ones((31, 31), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(tex, connectivity=8)
    h, w = gray.shape
    if n <= 1:
        return 0, 0, w, h
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, bw, bh = stats[i, :4]
    region = labels[y:y + bh, x:x + bw] == i
    cols = np.where(region.mean(0) >= 0.30)[0]
    rows = np.where(region.mean(1) >= 0.30)[0]
    if cols.size == 0 or rows.size == 0:
        return int(x), int(y), int(x + bw), int(y + bh)
    return int(x + cols[0]), int(y + rows[0]), int(x + cols[-1] + 1), int(y + rows[-1] + 1)


def colour_mask(sector: np.ndarray) -> np.ndarray:
    """Return pixels that are coloured relative to the image tint."""
    hsv = cv2.cvtColor(sector, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0].astype(np.int32), hsv[..., 1], hsv[..., 2]
    moderately = (sat > 35) & (val > 40)
    if moderately.mean() > 0.15:
        # A tinted display colours the whole image, so marks must differ from the dominant hue.
        hist = np.bincount(hue[moderately], minlength=180)
        tint = int(np.argmax(np.convolve(np.r_[hist, hist[:9]], np.ones(9), "same")[:180]))
        dist = np.minimum(np.abs(hue - tint), 180 - np.abs(hue - tint))
        return ((sat > 110) & (val > 110) & (dist > 15)).astype(np.uint8)
    return ((sat > 70) & (val > 80)).astype(np.uint8)


def cross_templates() -> list[np.ndarray]:
    temps = []
    for size in (7, 9, 11, 13, 15):
        c = size // 2
        plus = np.zeros((size, size), np.float32)
        plus[c, :] = 1
        plus[:, c] = 1
        ex = np.maximum(np.eye(size, dtype=np.float32), np.fliplr(np.eye(size, dtype=np.float32)))
        for shape in (plus, ex):
            temps.append(shape)
            hollow = shape.copy()
            hollow[c - 1:c + 2, c - 1:c + 2] = 0
            temps.append(hollow)
    return temps


TEMPLATES = cross_templates()


def achromatic_marks(gray: np.ndarray, thresh: float) -> list[tuple[int, int, int]]:
    """Find bright thin cross-shaped marks. Returns x, y, half-size."""
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))).astype(np.float32)
    hits = []
    for t in TEMPLATES:
        res = cv2.matchTemplate(tophat, t, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= thresh)
        for x, y in zip(xs, ys):
            patch = gray[y:y + t.shape[0], x:x + t.shape[1]]
            if patch[t > 0].mean() >= 130:  # rejects low-contrast speckle matches
                hits.append((float(res[y, x]), int(x + t.shape[1] // 2), int(y + t.shape[0] // 2), t.shape[0] // 2))
    hits.sort(reverse=True)
    kept: list[tuple[int, int, int]] = []
    for _, cx, cy, half in hits:
        if all((cx - k[0]) ** 2 + (cy - k[1]) ** 2 > 100 for k in kept):
            kept.append((cx, cy, half))
    return kept[:8]


@dataclass
class Detection:
    points: np.ndarray  # endpoint coordinates inside the sector
    mask: np.ndarray  # pixels to erase
    source: str  # colour, colour_line, achromatic, doppler or none
    n_clusters: int


def merge_close(points: list[tuple[float, float, float]], radius: float) -> list[tuple[float, float]]:
    """Merge a mark with its adjacent digit label, keeping the larger component's position."""
    ordered = sorted(points, key=lambda p: -p[2])
    kept: list[tuple[float, float]] = []
    for x, y, _ in ordered:
        if all((x - k[0]) ** 2 + (y - k[1]) ** 2 > radius ** 2 for k in kept):
            kept.append((x, y))
    return kept


def detect_marks(sector: np.ndarray, text_mask: np.ndarray, ach_thresh: float) -> Detection:
    h, w = sector.shape[:2]
    gray = cv2.cvtColor(sector, cv2.COLOR_BGR2GRAY)
    colour = colour_mask(sector)
    colour[text_mask > 0] = 0
    n, labels, stats, cents = cv2.connectedComponentsWithStats(colour, connectivity=8)

    # Flow signal forms filled blobs, which caliper strokes never do.
    filled = sum(int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 120
                 and stats[i, cv2.CC_STAT_AREA] / (stats[i, 2] * stats[i, 3]) > 0.35)
    if filled > 0.004 * h * w:
        return Detection(np.zeros((0, 2)), np.zeros((h, w), np.uint8), "doppler", 0)

    margin = max(5, int(0.03 * max(h, w)))
    ends, tiny = [], []
    erase = np.zeros((h, w), np.uint8)
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        cx, cy = cents[i]
        if area < 2 or cx < margin or cy < margin or cx > w - margin or cy > h - margin:
            continue
        erase[labels == i] = 1
        side = max(bw, bh)
        if side >= 23 and area / (bw * bh) < 0.30:
            # A solid measurement line merged with its marks: its extreme pixels are the endpoints.
            ys, xs = np.where(labels == i)
            pts = np.c_[xs, ys].astype(np.float32)
            axis = np.linalg.svd(pts - pts.mean(0), full_matrices=False)[2][0]
            proj = (pts - pts.mean(0)) @ axis
            ends += [(*pts[proj.argmin()], float(area)), (*pts[proj.argmax()], float(area))]
        elif 4 <= side <= 22 and area >= 6 and area / (bw * bh) <= 0.85:
            ends.append((float(cx), float(cy), float(area)))
        elif side <= 4:
            tiny.append((float(cx), float(cy), float(area)))

    points = merge_close(ends, 12.0)
    source = "colour"
    if len(points) < 2 and len(tiny) >= 4:
        # Very small marks: a dotted line still spans the two endpoints.
        pts = np.asarray([(t[0], t[1]) for t in tiny], np.float32)
        axis = np.linalg.svd(pts - pts.mean(0), full_matrices=False)[2][0]
        proj = (pts - pts.mean(0)) @ axis
        points = [tuple(pts[proj.argmin()]), tuple(pts[proj.argmax()])]
        source = "colour_line"
    if len(points) < 2:
        ach = [a for a in achromatic_marks(gray, ach_thresh)
               if margin < a[0] < w - margin and margin < a[1] < h - margin and text_mask[a[1], a[0]] == 0]
        for cx, cy, half in ach:
            cv2.rectangle(erase, (cx - half - 1, cy - half - 1), (cx + half + 1, cy + half + 1), 1, -1)
        points = [(float(a[0]), float(a[1])) for a in ach]
        source = "achromatic"
    if len(points) < 2:
        return Detection(np.zeros((0, 2)), erase, "none", 0)

    arr = np.asarray(points, float)
    cl = DBSCAN(eps=0.30 * max(h, w), min_samples=2).fit_predict(arr)
    valid = cl[cl >= 0]
    if valid.size == 0:
        return Detection(np.zeros((0, 2)), erase, "none", 0)
    main = np.bincount(valid).argmax()
    return Detection(arr[cl == main], erase, source, int(valid.max() + 1))


def load_ocr(image_uid: str, im: np.ndarray, cache: dict, engine) -> list[tuple[np.ndarray, str]]:
    """Run OCR at twice the resolution, because burned-in fonts are small, and cache the result."""
    if image_uid not in cache:
        up = cv2.resize(im, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        result, _ = engine(up)
        cache[image_uid] = [[(np.asarray(box, float) / 2).round(1).tolist(), str(text)] for box, text, _ in (result or [])]
    return [(np.asarray(box, np.int32), text) for box, text in cache[image_uid]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-root", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True, help="Git-ignored directory for manifest and aggregates")
    ap.add_argument("--cache-dir", type=Path, required=True, help="Private directory for cropped and erased images")
    ap.add_argument("--key-file", type=Path, required=True, help="Private pseudonym key")
    ap.add_argument("--ocr-cache", type=Path, required=True, help="Private OCR cache, which may contain identifiers")
    ap.add_argument("--ach-thresh", type=float, default=0.66)
    args = ap.parse_args()

    cache = json.loads(args.ocr_cache.read_text(encoding="utf-8")) if args.ocr_cache.exists() else {}
    engine = None
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.cache_dir / "raw").mkdir(parents=True, exist_ok=True)
    (args.cache_dir / "erased").mkdir(parents=True, exist_ok=True)
    args.key_file.parent.mkdir(parents=True, exist_ok=True)

    folders = sorted(p for p in args.raw_root.iterdir() if p.is_dir())
    key_rows, rows = [], []
    for pidx, folder in enumerate(folders, 1):
        patient = f"TH{pidx:03d}"
        key_rows.append((patient, folder.name))
        files = sorted(f for f in folder.iterdir() if f.suffix.lower() in {".jpg", ".jpeg"})
        for iidx, path in enumerate(files, 1):
            uid = f"{patient}_{iidx:02d}"
            im = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if im is None:
                continue
            if uid not in cache and engine is None:
                from rapidocr_onnxruntime import RapidOCR
                engine = RapidOCR()
            ocr = load_ocr(uid, im, cache, engine)
            scanner = infer_scanner(" ".join(t for _, t in ocr))

            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            full_text = np.zeros(gray.shape, np.uint8)
            for box, _ in ocr:
                cv2.fillPoly(full_text, [box], 1)
            full_text = cv2.dilate(full_text, np.ones((5, 5), np.uint8))

            x0, y0, x1, y1 = sector_box(gray, full_text)
            sector = im[y0:y1, x0:x1]
            text_mask = full_text[y0:y1, x0:x1]
            h, w = sector.shape[:2]

            det = detect_marks(sector, text_mask, args.ach_thresh)
            erase = cv2.dilate(det.mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            erase = ((erase > 0) | (text_mask > 0)).astype(np.uint8)
            erased = cv2.inpaint(sector, erase, 5, cv2.INPAINT_TELEA) if erase.any() else sector

            cv2.imwrite(str(args.cache_dir / "raw" / f"{uid}.png"), sector)
            cv2.imwrite(str(args.cache_dir / "erased" / f"{uid}.png"), erased)

            row = dict(
                image_uid=uid, patient=patient, scanner=scanner, sector_w=w, sector_h=h,
                source=det.source, n_marks=len(det.points), n_clusters=det.n_clusters,
                erased_frac=round(float(erase.mean()), 5),
                box_x0="", box_y0="", box_x1="", box_y1="", usable=0,
            )
            if len(det.points):
                bx0, by0 = det.points.min(0)
                bx1, by1 = det.points.max(0)
                bw, bh = bx1 - bx0, by1 - by0
                # A usable box has real extent, few marks and is not most of the sector.
                ok = (max(bw, bh) >= 0.05 * max(h, w) and bw * bh <= 0.5 * h * w and len(det.points) <= 8)
                row.update(box_x0=round(float(bx0), 1), box_y0=round(float(by0), 1), box_x1=round(float(bx1), 1),
                           box_y1=round(float(by1), 1), usable=int(ok))
            rows.append(row)
        if pidx % 50 == 0:
            print(f"processed {pidx}/{len(folders)} patients", flush=True)
            args.ocr_cache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    args.ocr_cache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    with args.key_file.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([("patient", "source_folder"), *key_rows])
    with (args.out_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    usable = sum(r["usable"] for r in rows)
    print(f"images={len(rows)} usable_boxes={usable} ({usable / len(rows):.1%})")
    for src in ("colour", "colour_line", "achromatic", "doppler", "none"):
        print(src, sum(r["source"] == src for r in rows))


if __name__ == "__main__":
    main()
