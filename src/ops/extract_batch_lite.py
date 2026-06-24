#!/usr/bin/env python3
"""Ultra-lightweight CT variant extraction for 2GB cgroup containers."""
import csv
import gc
import json
import re
import sys
from pathlib import Path

SIZE = 224
CT_ROOT = Path("/root/autodl-tmp/data/bimcv_ct_variants")
VARIANTS = ["mid", "3slice", "proj"]
OUT = {v: CT_ROOT / f"bimcv_ct_{v}" for v in VARIANTS}
for d in OUT.values():
    d.mkdir(parents=True, exist_ok=True)

# 1. Collect CV patients (no pandas)
cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")
patients = set()
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    with open(csv_p) as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["patient_id"].replace("bimcv_", "")
            patients.add(pid)
print(f"CV patients: {len(patients)}", flush=True)

# 2. Build nifti index
roots = [Path("/root/autodl-tmp/data/bimcv_paired"),
         Path("/root/autodl-tmp/data/bimcv_neg_paired")]
nifti = {}
for r in roots:
    if not r.exists():
        continue
    for p in r.glob("sub-*/ct/*.nii.gz"):
        m = re.search(r"S\d+", p.name)
        if m and m.group(0) not in nifti:
            nifti[m.group(0)] = p
print(f"NIfTI index: {len(nifti)}", flush=True)

matched = sorted(p for p in patients if p in nifti)
print(f"Matched: {len(matched)}", flush=True)

# 3. Process one at a time with lazy imports
done, skipped, errors = 0, 0, []
for i, pid in enumerate(matched):
    tag = f"bimcv_{pid}.png"
    if all((OUT[v] / tag).exists() for v in VARIANTS):
        skipped += 1
        done += 1
        continue

    # Lazy import to delay memory allocation
    import nibabel as nib
    import numpy as np
    from PIL import Image

    try:
        img = nib.load(str(nifti[pid]))
        vol = np.squeeze(img.get_fdata(dtype=np.float32))
        # Free the nibabel image immediately
        del img
        gc.collect()

        if vol.ndim != 3:
            raise ValueError(f"shape={vol.shape}")

        z = vol.shape[2]
        c = z // 2

        def norm(a):
            a = np.clip(a, -1000, 400)
            return ((a + 1000) / 1400 * 255).astype(np.uint8)

        # Mid slice
        mid = norm(vol[:, :, c])
        Image.fromarray(mid, "L").resize((SIZE, SIZE), Image.BILINEAR).save(OUT["mid"] / tag)
        del mid

        # 3-slice
        gap = 5
        idx = [max(0, c - gap), c, min(z - 1, c + gap)]
        stack = np.stack([norm(vol[:, :, j]) for j in idx], axis=-1)
        Image.fromarray(stack, "RGB").resize((SIZE, SIZE), Image.BILINEAR).save(OUT["3slice"] / tag)
        del stack

        # Projection
        proj = norm(np.mean(np.clip(vol, -1000, 400), axis=2))
        Image.fromarray(proj, "L").resize((SIZE, SIZE), Image.BILINEAR).save(OUT["proj"] / tag)
        del proj

        del vol
        gc.collect()
        done += 1
        print(f"  [{i+1}/{len(matched)}] {pid} OK", flush=True)
    except Exception as e:
        errors.append({"patient": pid, "error": str(e)})
        print(f"  [{i+1}/{len(matched)}] {pid} ERROR: {e}", flush=True)
        gc.collect()

print(f"\nDone: {done}/{len(matched)} (skipped={skipped}, errors={len(errors)})", flush=True)
summary = {"matched": len(matched), "processed": done, "skipped": skipped,
           "errors": errors, "missing_nifti": sorted(patients - set(nifti))}
Path("/root/autodl-tmp/logs/bimcv_h800_5fold_cv/extract_ct_variants_v2.json").write_text(
    json.dumps(summary, indent=2))
print("Summary written.", flush=True)
