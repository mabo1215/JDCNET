"""Build a pseudonymized manifest and caliper-derived weak lesion boxes.

For each thyroid ultrasound image this script:
  1. reads burned-in text locally, to mask it and to infer the scanner series,
  2. crops the imaging sector from local texture,
  3. rejects colour Doppler frames, whose flow signal would be mistaken for marks,
  4. searches tint-relative chroma for vivid caliper marks, and accepts them only when they form two
     crossing perpendicular measurements, or one measurement with a visible line,
  5. derives a weak lesion box from the accepted endpoints,
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
    ("philips", r"philips|epiq|affiniti|iu22|ie33|hd11|hd15|l12-5"),
    ("ge_logiq", r"logiq|voluson|\bs8\b"),
    ("mindray", r"mindra|resona|\bdc-?[0-9]{1,2}\b|iclear|ibeam|ssi1580|l14-5wu"),
    ("canon_aplio", r"aplio|canon|apure|precision"),
    ("xr80a", r"xr-?80|xrboa"),
    ("siemens_sequoia", r"sequoia|hmid|toggle|\bcal1\b"),
    ("siemens_s", r"siemens|\bs[123]000\b|juniper|acuson"),
    ("ultimus", r"ultimus|u5-15le"),
    ("hisense", "hisense|\u6d77\u4fe1"),
    ("toshiba_xario", r"xario|toshiba"),
    ("esaote_mylab", r"mylab|esaote"),
    # Interface-based groups: no vendor string was readable, so these only support cross-group comparison.
    ("ui_dist_ab", r"dist\s?[ab]\b|dista|distb"),
    ("ui_qscan", r"qscan|lx5|l3-12a"),
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
    h, w = gray.shape
    best = (0, 0, w, h)
    for std_thr, mean_thr in ((5, 12), (3, 8)):
        tex = ((std > std_thr) & (mean > mean_thr)).astype(np.uint8)
        tex[text_mask > 0] = 0
        tex = cv2.morphologyEx(tex, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        tex = cv2.morphologyEx(tex, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
        tex = cv2.morphologyEx(tex, cv2.MORPH_OPEN, np.ones((31, 31), np.uint8))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(tex, connectivity=8)
        if n <= 1:
            continue
        i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        x, y, bw, bh = stats[i, :4]
        region = labels[y:y + bh, x:x + bw] == i
        cols = np.where(region.mean(0) >= 0.30)[0]
        rows = np.where(region.mean(1) >= 0.30)[0]
        if cols.size and rows.size:
            best = (int(x + cols[0]), int(y + rows[0]), int(x + cols[-1] + 1), int(y + rows[-1] + 1))
        else:
            best = (int(x), int(y), int(x + bw), int(y + bh))
        if (best[2] - best[0]) * (best[3] - best[1]) >= 0.20 * h * w:
            return best
    return best


def cross_templates() -> list[tuple[np.ndarray, int, int]]:
    """Return cross templates as (template, family, size), where family 0 is plus and 1 is X."""
    temps = []
    for size in (7, 9, 11, 13, 15, 17, 19):
        c = size // 2
        plus = np.zeros((size, size), np.float32)
        plus[c, :] = 1
        plus[:, c] = 1
        ex = np.maximum(np.eye(size, dtype=np.float32), np.fliplr(np.eye(size, dtype=np.float32)))
        for family, shape in enumerate((plus, ex)):
            temps.append((shape, family, size))
            hollow = shape.copy()
            hollow[c - 1:c + 2, c - 1:c + 2] = 0
            temps.append((hollow, family, size))
            if size >= 11:
                temps.append((cv2.dilate(shape, np.ones((3, 3), np.uint8)), family, size))
    return temps


TEMPLATES = cross_templates()


def residual_chroma(sector: np.ndarray) -> np.ndarray:
    """Return chroma after removing the tint-versus-brightness trend of the image."""
    lab = cv2.cvtColor(sector, cv2.COLOR_BGR2LAB).astype(np.float32)
    lum, a, b = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    bright = lum > 40
    ka, kb = (np.median(a[bright] / lum[bright]), np.median(b[bright] / lum[bright])) if bright.sum() >= 100 else (0.0, 0.0)
    return np.hypot(a - ka * lum, b - kb * lum)


def colour_mask(chroma: np.ndarray, lum: np.ndarray) -> np.ndarray:
    med = float(np.median(chroma))
    mad = 1.4826 * float(np.median(np.abs(chroma - med)))
    return ((chroma > max(9.0, med + 6 * mad)) & (lum > 35)).astype(np.uint8)


def find_candidates(maps: list[tuple[np.ndarray, float]], text_mask: np.ndarray, margin: int,
                    ncc_thresh: float, limit: int = 30) -> np.ndarray:
    """Return candidate marks as rows of x, y, score, family, size, channel."""
    h, w = text_mask.shape
    hits = []
    for channel, (image, min_strength) in enumerate(maps):
        for t, family, size in TEMPLATES:
            ncc = cv2.matchTemplate(image, t, cv2.TM_CCOEFF_NORMED)
            strength = cv2.matchTemplate(image, t, cv2.TM_CCORR) / t.sum()
            ys, xs = np.where((ncc >= ncc_thresh) & (strength >= min_strength))
            for x, y in zip(xs, ys):
                cx, cy = int(x + size // 2), int(y + size // 2)
                if margin < cx < w - margin and margin < cy < h - margin and text_mask[cy, cx] == 0:
                    hits.append((cx, cy, float(ncc[y, x]), family, size, channel))
    hits.sort(key=lambda r: -r[2])
    kept: list[tuple] = []
    for hit in hits:
        if all((hit[0] - k[0]) ** 2 + (hit[1] - k[1]) ** 2 > 36 for k in kept):
            kept.append(hit)
            if len(kept) == limit:
                break
    return np.asarray(kept, float).reshape(-1, 6)


def matching_pairs(c: np.ndarray, min_len: float, max_len: float) -> tuple[np.ndarray, np.ndarray]:
    """Return index pairs that could be the two ends of one measurement."""
    i, j = np.triu_indices(len(c), 1)
    same = (c[i, 3] == c[j, 3]) & (c[i, 5] == c[j, 5]) & (np.abs(c[i, 4] - c[j, 4]) <= 4)
    length = np.hypot(c[i, 0] - c[j, 0], c[i, 1] - c[j, 1])
    keep = same & (length >= min_len) & (length <= max_len)
    return i[keep], j[keep]


def orthogonal_measurement(c: np.ndarray, min_len: float, max_len: float, min_score: float) -> np.ndarray | None:
    """Find two crossing, roughly perpendicular measurements, as drawn for long and short axes."""
    if len(c) < 4:
        return None
    i, j = matching_pairs(c, min_len, max_len)
    if len(i) < 2:
        return None
    start = c[i][:, :2]
    vec = c[j][:, :2] - start
    length = np.hypot(vec[:, 0], vec[:, 1])
    a, b = np.triu_indices(len(i), 1)
    cross = vec[a, 0] * vec[b, 1] - vec[a, 1] * vec[b, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = start[b] - start[a]
        t = (delta[:, 0] * vec[b, 1] - delta[:, 1] * vec[b, 0]) / cross
        u = (delta[:, 0] * vec[a, 1] - delta[:, 1] * vec[a, 0]) / cross
        sine = np.abs(cross) / (length[a] * length[b])
    disjoint = (i[a] != i[b]) & (i[a] != j[b]) & (j[a] != i[b]) & (j[a] != j[b])
    ratio = np.minimum(length[a], length[b]) / np.maximum(length[a], length[b])
    ok = disjoint & (t > 0.1) & (t < 0.9) & (u > 0.1) & (u < 0.9) & (sine >= 0.90) & (ratio >= 0.25)
    if not ok.any():
        return None
    score = (c[i[a], 2] + c[j[a], 2] + c[i[b], 2] + c[j[b], 2]) / 4
    score[~ok] = -1
    best = int(np.argmax(score))
    if score[best] < min_score:
        return None
    return c[[i[a[best]], j[a[best]], i[b[best]], j[b[best]]], :2]


def single_measurement(c: np.ndarray, line_map: np.ndarray, min_len: float, max_len: float,
                       min_score: float) -> np.ndarray | None:
    """Find one measurement: two matching marks joined by a visible dotted or solid line."""
    if len(c) < 2:
        return None
    i, j = matching_pairs(c, min_len, max_len)
    best, best_score = None, min_score
    for p, q in zip(i, j):
        score = (c[p, 2] + c[q, 2]) / 2
        if score <= best_score:
            continue
        n = int(np.hypot(*(c[p, :2] - c[q, :2])))
        ts = np.linspace(0.1, 0.9, max(n, 2))
        xs = (c[p, 0] + ts * (c[q, 0] - c[p, 0])).astype(int)
        ys = (c[p, 1] + ts * (c[q, 1] - c[p, 1])).astype(int)
        if line_map[ys, xs].mean() >= 0.30:
            best, best_score = c[[p, q], :2], score
    return best


@dataclass
class Detection:
    points: np.ndarray  # measurement endpoints inside the sector
    mask: np.ndarray  # pixels to erase
    source: str  # orthogonal, single, doppler or none
    n_clusters: int


def detect_marks(sector: np.ndarray, text_mask: np.ndarray, ach_thresh: float) -> Detection:
    h, w = sector.shape[:2]
    gray = cv2.cvtColor(sector, cv2.COLOR_BGR2GRAY)
    lum = cv2.cvtColor(sector, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    chroma = residual_chroma(sector)
    colour = colour_mask(chroma, lum)
    colour[text_mask > 0] = 0
    hue = cv2.cvtColor(sector, cv2.COLOR_BGR2HSV)[..., 0].astype(np.int32)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(colour, connectivity=8)

    # Flow signal forms filled red or blue blobs. Caliper marks are yellow, green or thin.
    flow = 0
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area > 120 and area / (stats[i, 2] * stats[i, 3]) > 0.35:
            hv = hue[labels == i]
            if (((hv <= 15) | (hv >= 165) | ((hv >= 95) & (hv <= 135))).mean()) >= 0.6:
                flow += area
    if flow > 0.004 * h * w:
        return Detection(np.zeros((0, 2)), np.zeros((h, w), np.uint8), "doppler", 0)

    side = max(h, w)
    margin = max(5, int(0.03 * side))
    min_len, max_len = 0.05 * side, 0.80 * side
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))).astype(np.float32)
    # Luminance candidates produced many false measurements on speckle during development, so only
    # vivid coloured marks are accepted. This trades coverage for precision.
    maps = [(np.minimum(chroma, 60.0), 25.0)]
    cand = find_candidates(maps, text_mask, margin, ach_thresh - 0.07, limit=14)

    erase = np.zeros((h, w), np.uint8)
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if 2 <= area <= 0.01 * h * w:
            erase[labels == i] = 1

    points = orthogonal_measurement(cand, min_len, max_len, ach_thresh)
    source = "orthogonal"
    if points is None:
        line_map = cv2.dilate(colour, np.ones((3, 3), np.uint8))
        points = single_measurement(cand, line_map, min_len, max_len, ach_thresh + 0.04)
        source = "single"
    if points is None:
        return Detection(np.zeros((0, 2)), erase, "none", 0)

    # Erase the marks and any bright or coloured line pixels between them, whatever their colour.
    for x, y in points.astype(int):
        cv2.rectangle(erase, (x - 10, y - 10), (x + 10, y + 10), 1, -1)
    strokes = np.zeros((h, w), np.uint8)
    pairs = [(0, 1), (2, 3)] if len(points) == 4 else [(0, 1)]
    for p, q in pairs:
        cv2.line(strokes, tuple(int(v) for v in points[p]), tuple(int(v) for v in points[q]), 1, 3)
    erase[(strokes > 0) & ((tophat > 25) | (colour > 0))] = 1
    # A full square would blank tissue, so inside each square keep only pixels that look like strokes.
    square = np.zeros((h, w), np.uint8)
    for x, y in points.astype(int):
        cv2.rectangle(square, (x - 10, y - 10), (x + 10, y + 10), 1, -1)
    erase[(square > 0) & (tophat <= 15) & (colour == 0)] = 0
    return Detection(points, erase, source, len(pairs))


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
    ap.add_argument("--ach-thresh", type=float, default=0.62, help="Minimum mean template score of a measurement")
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
            erase = cv2.dilate(det.mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
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
                # A usable box has real extent and is not most of the sector.
                ok = max(bw, bh) >= 0.05 * max(h, w) and bw * bh <= 0.5 * h * w
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
    for src in ("orthogonal", "single", "doppler", "none"):
        print(src, sum(r["source"] == src for r in rows))


if __name__ == "__main__":
    main()
