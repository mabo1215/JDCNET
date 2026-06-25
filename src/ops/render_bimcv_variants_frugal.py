#!/usr/bin/env python3
"""Memory-frugal CT teacher-variant renderer for 无卡(low-RAM) mode.
Renders ONLY mid + 3slice (calibrated_gate does not use proj), reading
individual slices lazily via dataobj[:,:,idx] so the full volume is never
loaded into RAM. Idempotent: skips patients whose mid+3slice already exist.
Matches extract_ct_teacher_variants.py params: HU clip [-1000,400], size 224,
3slice gap = round(5mm / z_spacing)."""
import glob, os, re, sys, json
import numpy as np
import nibabel as nib
from PIL import Image

ROOTS = ["/root/autodl-tmp/data/bimcv_paired", "/root/autodl-tmp/data/bimcv_neg_paired"]
OUT = "/root/autodl-tmp/data/bimcv_ct_variants"
MID = os.path.join(OUT, "bimcv_ct_mid")
S3 = os.path.join(OUT, "bimcv_ct_3slice")
os.makedirs(MID, exist_ok=True); os.makedirs(S3, exist_ok=True)
SIZE = 224

def pid_of(p):
    m = re.search(r"S\d+", p); return m.group(0) if m else None

def norm(a):
    a = np.clip(np.asarray(a, dtype=np.float32), -1000.0, 400.0)
    a = (a + 1000.0) / 1400.0
    return (a * 255.0).astype(np.uint8)

# build nifti index (first .nii per patient)
idx = {}
for root in ROOTS:
    for p in sorted(glob.glob(root + "/sub-*/ct/*.nii") + glob.glob(root + "/sub-*/ct/*.nii.gz")):
        pid = pid_of(p)
        if pid and pid not in idx:
            idx[pid] = p

done = skipped = err = 0
errors = []
for pid, path in sorted(idx.items()):
    mp = os.path.join(MID, f"bimcv_{pid}.png"); sp = os.path.join(S3, f"bimcv_{pid}.png")
    if os.path.exists(mp) and os.path.getsize(mp) > 0 and os.path.exists(sp) and os.path.getsize(sp) > 0:
        skipped += 1; continue
    try:
        img = nib.load(path)
        shp = img.shape
        if len(shp) < 3:
            raise ValueError(f"not 3D: {shp}")
        z = shp[2]; c = z // 2
        zm = img.header.get_zooms(); zsp = zm[2] if len(zm) > 2 and zm[2] > 0 else 1.0
        gap = max(1, int(round(5.0 / zsp)))
        ids = [max(0, c - gap), c, min(z - 1, c + gap)]
        do = img.dataobj
        mid = norm(np.squeeze(do[:, :, c]))
        Image.fromarray(mid, "L").resize((SIZE, SIZE), Image.BILINEAR).save(mp)
        stack = np.stack([norm(np.squeeze(do[:, :, i])) for i in ids], axis=-1)
        Image.fromarray(stack, "RGB").resize((SIZE, SIZE), Image.BILINEAR).save(sp)
        done += 1
        del img, do
    except Exception as e:
        err += 1; errors.append({"pid": pid, "path": path, "err": repr(e)})
    if (done + err) % 25 == 0 and (done + err) > 0:
        print(f"progress: done={done} skipped={skipped} err={err}", flush=True)

summary = {"nifti_subjects": len(idx), "rendered": done, "skipped_existing": skipped,
           "errors": err, "error_detail": errors[:20],
           "final_mid": len(glob.glob(MID + "/bimcv_S*.png")),
           "final_3slice": len(glob.glob(S3 + "/bimcv_S*.png"))}
os.makedirs("/root/autodl-tmp/logs", exist_ok=True)
json.dump(summary, open("/root/autodl-tmp/logs/render_frugal_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2), flush=True)
print("RENDER_FRUGAL_DONE", flush=True)
