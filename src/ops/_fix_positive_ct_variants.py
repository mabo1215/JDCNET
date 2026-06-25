#!/usr/bin/env python3
"""Populate CT variant directories with positive patient CT slices.

The old bimcv_ct_slices directory has 114 mid-slice CT images (512x512 L)
for positive patients. These need to be resized to 224x224 and placed in:
  - bimcv_ct_mid/bimcv_{pid}.png   (grayscale, resized)
  - bimcv_ct_3slice/bimcv_{pid}.png (RGB, mid replicated to 3 channels)
  - bimcv_ct_proj/bimcv_{pid}.png   (grayscale, same as mid for single slice)

For negative patients that already have proper 3-slice and projection variants
extracted from NIfTI volumes, this script does not overwrite them.
"""
import re
from pathlib import Path
from PIL import Image
import numpy as np

SIZE = 224
OLD_DIR = Path("/root/autodl-tmp/data/bimcv/bimcv_ct_slices")
CT_ROOT = Path("/root/autodl-tmp/data/bimcv_ct_variants")
MID_DIR = CT_ROOT / "bimcv_ct_mid"
SLICE_DIR = CT_ROOT / "bimcv_ct_3slice"
PROJ_DIR = CT_ROOT / "bimcv_ct_proj"

for d in [MID_DIR, SLICE_DIR, PROJ_DIR]:
    d.mkdir(parents=True, exist_ok=True)

created = {"mid": 0, "3slice": 0, "proj": 0}
skipped = 0

for src in sorted(OLD_DIR.glob("S*_ct_mid.png")):
    m = re.search(r"S\d+", src.name)
    if not m:
        continue
    pid = m.group(0)
    tag = f"bimcv_{pid}.png"

    mid_out = MID_DIR / tag
    slice_out = SLICE_DIR / tag
    proj_out = PROJ_DIR / tag

    # Skip if all variants already exist (e.g., negative patients with NIfTI-extracted data)
    if mid_out.exists() and slice_out.exists() and proj_out.exists():
        skipped += 1
        continue

    im = Image.open(src).convert("L")
    im_resized = im.resize((SIZE, SIZE), Image.BILINEAR)
    arr = np.array(im_resized)

    # Mid slice
    if not mid_out.exists():
        im_resized.save(mid_out)
        created["mid"] += 1

    # 3-slice: replicate grayscale to 3 channels
    if not slice_out.exists():
        rgb = np.stack([arr, arr, arr], axis=-1)
        Image.fromarray(rgb, "RGB").save(slice_out)
        created["3slice"] += 1

    # Projection: same as mid for single-slice source
    if not proj_out.exists():
        im_resized.save(proj_out)
        created["proj"] += 1

print(f"Created: mid={created['mid']}, 3slice={created['3slice']}, proj={created['proj']}")
print(f"Skipped (already exist): {skipped}")
print(f"Total mid: {len(list(MID_DIR.glob('bimcv_S*.png')))}")
print(f"Total 3slice: {len(list(SLICE_DIR.glob('bimcv_S*.png')))}")
print(f"Total proj: {len(list(PROJ_DIR.glob('bimcv_S*.png')))}")
