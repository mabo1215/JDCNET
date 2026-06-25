#!/usr/bin/env python3
"""CT variant extraction using memory-mapped NIfTI loading for 2GB containers."""
import csv
import gc
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SIZE = 224
CT_ROOT = Path("/root/autodl-tmp/data/bimcv_ct_variants")
OUT = {"mid": CT_ROOT / "bimcv_ct_mid",
       "3slice": CT_ROOT / "bimcv_ct_3slice",
       "proj": CT_ROOT / "bimcv_ct_proj"}
for d in OUT.values():
    d.mkdir(parents=True, exist_ok=True)

# 1. Collect CV patients
cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")
patients = set()
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    with open(csv_p) as f:
        for row in csv.DictReader(f):
            patients.add(row["patient_id"].replace("bimcv_", ""))

# 2. Build nifti index
nifti = {}
for r in ["/root/autodl-tmp/data/bimcv_paired", "/root/autodl-tmp/data/bimcv_neg_paired"]:
    rp = Path(r)
    if not rp.exists():
        continue
    for p in rp.glob("sub-*/ct/*.nii.gz"):
        m = re.search(r"S\d+", p.name)
        if m and m.group(0) not in nifti:
            nifti[m.group(0)] = str(p)

matched = sorted(p for p in patients if p in nifti)
print(f"Patients={len(patients)}, NIfTI={len(nifti)}, Matched={len(matched)}", flush=True)

# 3. Process each patient in a subprocess to guarantee memory cleanup
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

worker_path = "/root/autodl-tmp/_extract_worker.py"
with open(worker_path, "w") as f:
    f.write(WORKER)

done, skipped, errors = 0, 0, []
for i, pid in enumerate(matched):
    tag = f"bimcv_{pid}.png"
    if all((OUT[v] / tag).exists() for v in OUT):
        skipped += 1
        done += 1
        continue
    try:
        result = subprocess.run(
            ["/root/miniconda3/bin/python", worker_path, nifti[pid], pid, str(SIZE)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and "OK" in result.stdout:
            done += 1
            print(f"  [{i+1}/{len(matched)}] {pid} OK", flush=True)
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else f"rc={result.returncode}"
            errors.append({"patient": pid, "error": err})
            print(f"  [{i+1}/{len(matched)}] {pid} FAIL: {err}", flush=True)
    except subprocess.TimeoutExpired:
        errors.append({"patient": pid, "error": "timeout"})
        print(f"  [{i+1}/{len(matched)}] {pid} TIMEOUT", flush=True)
    except Exception as e:
        errors.append({"patient": pid, "error": str(e)})
        print(f"  [{i+1}/{len(matched)}] {pid} ERROR: {e}", flush=True)

print(f"\nDone: {done}/{len(matched)} (skipped={skipped}, errors={len(errors)})", flush=True)
summary = {"matched": len(matched), "processed": done, "skipped": skipped,
           "errors": errors, "missing_nifti": sorted(patients - set(nifti))}
Path("/root/autodl-tmp/logs/bimcv_h800_5fold_cv/extract_ct_variants_v2.json").write_text(
    json.dumps(summary, indent=2))
print("Summary written.", flush=True)
