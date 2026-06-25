#!/usr/bin/env python3
"""Lightweight batch CT variant extraction - processes one NIfTI at a time."""
import gc, re, json, sys
from pathlib import Path
import nibabel as nib
import numpy as np
import pandas as pd
from PIL import Image

SIZE = 224
CT_ROOT = Path("/root/autodl-tmp/data/bimcv_ct_variants")
VARIANTS = {"mid": CT_ROOT / "bimcv_ct_mid",
             "3slice": CT_ROOT / "bimcv_ct_3slice",
             "proj": CT_ROOT / "bimcv_ct_proj"}
for d in VARIANTS.values():
    d.mkdir(parents=True, exist_ok=True)

# 1. Collect CV patients
cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")
patients = set()
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    df = pd.read_csv(csv_p)
    patients.update(str(x).replace("bimcv_", "") for x in df["patient_id"].unique())

# 2. Build nifti index (one pass)
roots = [Path("/root/autodl-tmp/data/bimcv_paired"),
         Path("/root/autodl-tmp/data/bimcv_neg_paired")]
nifti = {}
for r in roots:
    for p in r.glob("sub-*/ct/*.nii.gz"):
        m = re.search(r"S\d+", str(p))
        if m and m.group(0) not in nifti:
            nifti[m.group(0)] = p

matched = sorted(p for p in patients if p in nifti)
print(f"Matched: {len(matched)} patients with NIfTI out of {len(patients)}", flush=True)

# 3. Process one at a time
done, errors = 0, []
for i, pid in enumerate(matched):
    tag = f"bimcv_{pid}.png"
    if all((VARIANTS[v] / tag).exists() for v in VARIANTS):
        done += 1
        continue
    try:
        img = nib.load(str(nifti[pid]))
        vol = np.squeeze(np.asarray(img.get_fdata(dtype=np.float32)))
        if vol.ndim != 3:
            raise ValueError(f"shape={vol.shape}")
        z = vol.shape[2]
        c = z // 2
        sp = img.header.get_zooms()
        gap = max(1, int(round(5.0 / (sp[2] if len(sp) > 2 and sp[2] > 0 else 1.0))))
        idx = [max(0, c - gap), c, min(z - 1, c + gap)]

        def norm(a):
            a = np.clip(a, -1000, 400)
            return ((a + 1000) / 1400 * 255).astype(np.uint8)

        mid = norm(vol[:, :, c])
        Image.fromarray(mid, "L").resize((SIZE, SIZE), Image.BILINEAR).save(VARIANTS["mid"] / tag)

        stack = np.stack([norm(vol[:, :, j]) for j in idx], axis=-1)
        Image.fromarray(stack, "RGB").resize((SIZE, SIZE), Image.BILINEAR).save(VARIANTS["3slice"] / tag)

        proj = norm(np.mean(np.clip(vol, -1000, 400), axis=2))
        Image.fromarray(proj, "L").resize((SIZE, SIZE), Image.BILINEAR).save(VARIANTS["proj"] / tag)

        done += 1
        del vol, img
        gc.collect()
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(matched)}] done={done}", flush=True)
    except Exception as e:
        errors.append({"patient": pid, "error": str(e)})
        print(f"  ERROR {pid}: {e}", flush=True)

print(f"\nFinished: {done}/{len(matched)} processed, {len(errors)} errors", flush=True)
summary = {"matched": len(matched), "processed": done, "errors": errors,
           "missing_nifti": sorted(patients - set(nifti))}
Path("/root/autodl-tmp/logs/bimcv_h800_5fold_cv/extract_ct_variants_v2.json").write_text(
    json.dumps(summary, indent=2))
print("Summary written.", flush=True)
