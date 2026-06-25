#!/usr/bin/env python3
"""Extract CT variants for newly downloaded positive patients.

For patients with NIfTI CT volumes: extract proper mid/3slice/proj variants.
For patients with only CXR (no NIfTI): use old pre-extracted mid slices if available,
creating synthetic 3slice and proj from the mid.
"""
import csv
import gc
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 224
BIMCV_PAIRED = Path("/root/autodl-tmp/bimcv_paired")
OLD_CT_SLICES = Path("/root/autodl-tmp/data/bimcv/bimcv_ct_slices")
CT_ROOT = Path("/root/autodl-tmp/data/bimcv_ct_variants")
MID_DIR = CT_ROOT / "bimcv_ct_mid"
SLICE_DIR = CT_ROOT / "bimcv_ct_3slice"
PROJ_DIR = CT_ROOT / "bimcv_ct_proj"

for d in [MID_DIR, SLICE_DIR, PROJ_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Collect all positive patient IDs from bimcv_paired
pos_patients = set()
for d in BIMCV_PAIRED.glob("sub-S*"):
    if d.is_dir():
        m = re.search(r"S\d+", d.name)
        if m:
            pos_patients.add(m.group(0))
print(f"Positive patients in bimcv_paired: {len(pos_patients)}")

# Find which ones need CT variants
need_extract = []
for pid in sorted(pos_patients):
    tag = f"bimcv_{pid}.png"
    if (MID_DIR / tag).exists() and (SLICE_DIR / tag).exists() and (PROJ_DIR / tag).exists():
        continue
    need_extract.append(pid)
print(f"Need CT variant extraction: {len(need_extract)}")

# Check NIfTI availability for these patients
nifti_map = {}
for pid in need_extract:
    ct_dir = BIMCV_PAIRED / f"sub-{pid}" / "ct"
    if ct_dir.exists():
        niftis = list(ct_dir.glob("*.nii.gz")) + list(ct_dir.glob("*.nii"))
        if niftis:
            # Pick largest NIfTI
            best = max(niftis, key=lambda x: x.stat().st_size)
            nifti_map[pid] = best

print(f"Have NIfTI: {len(nifti_map)}, no NIfTI: {len(need_extract) - len(nifti_map)}")

# --- Phase 1: Extract from NIfTI volumes using subprocess isolation ---
WORKER = '''
import gc, sys
import nibabel as nib
import numpy as np
from PIL import Image

nifti_path, pid, size = sys.argv[1], sys.argv[2], int(sys.argv[3])
out_mid = f"/root/autodl-tmp/data/bimcv_ct_variants/bimcv_ct_mid/bimcv_{pid}.png"
out_3s  = f"/root/autodl-tmp/data/bimcv_ct_variants/bimcv_ct_3slice/bimcv_{pid}.png"
out_proj = f"/root/autodl-tmp/data/bimcv_ct_variants/bimcv_ct_proj/bimcv_{pid}.png"

img = nib.load(nifti_path)
vol = np.squeeze(img.get_fdata(dtype=np.float32))
del img; gc.collect()
if vol.ndim != 3:
    raise ValueError(f"bad shape {vol.shape}")
z = vol.shape[2]
c = z // 2

def norm(a):
    a = np.clip(a, -1000, 400)
    return ((a + 1000) / 1400 * 255).astype(np.uint8)

mid = norm(vol[:, :, c])
Image.fromarray(mid, "L").resize((size, size), Image.BILINEAR).save(out_mid)
del mid

gap = 5
idx = [max(0, c - gap), c, min(z - 1, c + gap)]
stack = np.stack([norm(vol[:, :, j]) for j in idx], axis=-1)
Image.fromarray(stack, "RGB").resize((size, size), Image.BILINEAR).save(out_3s)
del stack

proj = norm(np.mean(np.clip(vol, -1000, 400), axis=2))
Image.fromarray(proj, "L").resize((size, size), Image.BILINEAR).save(out_proj)
print("OK")
'''

worker_path = Path("/root/autodl-tmp/_extract_worker_pos.py")
worker_path.write_text(WORKER)

nifti_done, nifti_errors = 0, []
for i, pid in enumerate(sorted(nifti_map)):
    tag = f"bimcv_{pid}.png"
    if (MID_DIR / tag).exists() and (SLICE_DIR / tag).exists() and (PROJ_DIR / tag).exists():
        nifti_done += 1
        continue
    try:
        result = subprocess.run(
            ["/root/miniconda3/bin/python", str(worker_path), str(nifti_map[pid]), pid, str(SIZE)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and "OK" in result.stdout:
            nifti_done += 1
            print(f"  NIfTI [{i+1}/{len(nifti_map)}] {pid} OK", flush=True)
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else f"rc={result.returncode}"
            nifti_errors.append({"patient": pid, "error": err})
            print(f"  NIfTI [{i+1}/{len(nifti_map)}] {pid} FAIL: {err}", flush=True)
    except subprocess.TimeoutExpired:
        nifti_errors.append({"patient": pid, "error": "timeout"})
        print(f"  NIfTI [{i+1}/{len(nifti_map)}] {pid} TIMEOUT", flush=True)

print(f"\nNIfTI extraction: {nifti_done}/{len(nifti_map)} done, {len(nifti_errors)} errors")

# --- Phase 2: Fallback to old CT mid slices for patients without NIfTI ---
fallback_done = 0
for pid in sorted(need_extract):
    if pid in nifti_map:
        continue  # already handled above
    tag = f"bimcv_{pid}.png"
    if (MID_DIR / tag).exists() and (SLICE_DIR / tag).exists() and (PROJ_DIR / tag).exists():
        fallback_done += 1
        continue
    # Check old CT slices
    old_mid = OLD_CT_SLICES / f"{pid}_ct_mid.png"
    if old_mid.exists():
        im = Image.open(old_mid).convert("L").resize((SIZE, SIZE), Image.BILINEAR)
        arr = np.array(im)
        if not (MID_DIR / tag).exists():
            im.save(MID_DIR / tag)
        if not (SLICE_DIR / tag).exists():
            rgb = np.stack([arr, arr, arr], axis=-1)
            Image.fromarray(rgb, "RGB").save(SLICE_DIR / tag)
        if not (PROJ_DIR / tag).exists():
            im.save(PROJ_DIR / tag)
        fallback_done += 1
        print(f"  Fallback {pid} OK (old mid slice)", flush=True)
    else:
        print(f"  Fallback {pid} SKIP (no NIfTI, no old mid slice)", flush=True)

print(f"\nFallback: {fallback_done} done")
print(f"\nFinal counts:")
print(f"  mid: {len(list(MID_DIR.glob('bimcv_S*.png')))}")
print(f"  3slice: {len(list(SLICE_DIR.glob('bimcv_S*.png')))}")
print(f"  proj: {len(list(PROJ_DIR.glob('bimcv_S*.png')))}")
