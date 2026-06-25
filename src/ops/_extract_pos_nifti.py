#!/usr/bin/env python3
"""Extract real CT variants from newly downloaded positive patient NIfTI volumes.
Uses subprocess isolation to avoid OOM on large volumes.
Falls back to old mid slices for patients without NIfTI.
"""
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
PY = "/root/miniconda3/bin/python"

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

worker_path = Path("/root/autodl-tmp/_worker_pos_nifti.py")
worker_path.write_text(WORKER)

# Build NIfTI index for positive patients
nifti_map = {}
for d in sorted(BIMCV_PAIRED.glob("sub-S*")):
    m = re.search(r"S\d+", d.name)
    if not m:
        continue
    pid = m.group(0)
    ct_dir = d / "ct"
    if ct_dir.exists():
        niftis = list(ct_dir.glob("*.nii.gz")) + list(ct_dir.glob("*.nii"))
        if niftis:
            nifti_map[pid] = max(niftis, key=lambda x: x.stat().st_size)

print(f"Positive patients with NIfTI: {len(nifti_map)}")

# Extract from NIfTI (overwrite synthetic versions with real ones)
done, errors = 0, []
for i, (pid, npath) in enumerate(sorted(nifti_map.items())):
    try:
        result = subprocess.run(
            [PY, str(worker_path), str(npath), pid, str(SIZE)],
            capture_output=True, text=True, timeout=180
        )
        if result.returncode == 0 and "OK" in result.stdout:
            done += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(nifti_map)}] {pid} OK", flush=True)
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else f"rc={result.returncode}"
            errors.append(pid)
            print(f"  [{i+1}/{len(nifti_map)}] {pid} FAIL: {err}", flush=True)
    except subprocess.TimeoutExpired:
        errors.append(pid)
        print(f"  [{i+1}/{len(nifti_map)}] {pid} TIMEOUT", flush=True)

print(f"\nNIfTI extraction: {done}/{len(nifti_map)} done, {len(errors)} errors")
if errors:
    print(f"  Failed: {errors}")

# Fallback: patients with old mid slices but no NIfTI
all_pos = {re.search(r"S\d+", d.name).group(0) for d in BIMCV_PAIRED.glob("sub-S*") if re.search(r"S\d+", d.name)}
no_nifti = sorted(all_pos - set(nifti_map))
fallback = 0
for pid in no_nifti:
    tag = f"bimcv_{pid}.png"
    if (MID_DIR / tag).exists() and (SLICE_DIR / tag).exists() and (PROJ_DIR / tag).exists():
        fallback += 1
        continue
    old_mid = OLD_CT_SLICES / f"{pid}_ct_mid.png"
    if old_mid.exists():
        im = Image.open(old_mid).convert("L").resize((SIZE, SIZE), Image.BILINEAR)
        arr = np.array(im)
        im.save(MID_DIR / tag)
        Image.fromarray(np.stack([arr, arr, arr], axis=-1), "RGB").save(SLICE_DIR / tag)
        im.save(PROJ_DIR / tag)
        fallback += 1
        print(f"  Fallback {pid} OK", flush=True)

print(f"Fallback (old mid): {fallback}/{len(no_nifti)}")
print(f"\nFinal: mid={len(list(MID_DIR.glob('bimcv_S*.png')))}, "
      f"3slice={len(list(SLICE_DIR.glob('bimcv_S*.png')))}, "
      f"proj={len(list(PROJ_DIR.glob('bimcv_S*.png')))}")
