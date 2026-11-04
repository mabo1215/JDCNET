"""Render numbered weak-box overlays for visual quality control of caliper extraction."""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def tile(img: np.ndarray, row, index: int, size: tuple[int, int]) -> np.ndarray:
    tw, th = size
    if row.usable == 1:
        p0 = (int(row.box_x0) - 3, int(row.box_y0) - 3)
        p1 = (int(row.box_x1) + 3, int(row.box_y1) + 3)
        cv2.rectangle(img, p0, p1, (0, 255, 255), 1)
    out = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
    cv2.rectangle(out, (0, 0), (46, 18), (0, 0, 0), -1)
    cv2.putText(out, str(index), (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--cache-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--usable", type=int, default=1)
    ap.add_argument("--skip", type=int, default=0, help="Skip this many sampled images, for a second page")
    ap.add_argument("--cols", type=int, default=6)
    args = ap.parse_args()

    df = pd.read_csv(args.manifest)
    pool = df[df.usable == args.usable].sample(frac=1.0, random_state=args.seed)
    chosen = pool.iloc[args.skip:args.skip + args.n]
    tiles = []
    for idx, row in enumerate(chosen.itertuples(), args.skip + 1):
        img = cv2.imread(str(args.cache_dir / "raw" / f"{row.image_uid}.png"))
        tiles.append(tile(img, row, idx, (320, 240)))
    while len(tiles) % args.cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + args.cols]) for i in range(0, len(tiles), args.cols)]
    cv2.imwrite(str(args.out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(chosen[["image_uid", "scanner", "source", "n_marks", "n_clusters"]].to_string(index=False))


if __name__ == "__main__":
    main()
