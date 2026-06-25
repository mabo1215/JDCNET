#!/usr/bin/env python3
"""Check image properties of old vs new CT slices."""
from PIL import Image
from pathlib import Path

# Old positive CT slices
old_dir = Path("/root/autodl-tmp/data/bimcv/bimcv_ct_slices")
samples = sorted(old_dir.glob("S*_ct_mid.png"))[:3]
print("=== Old positive CT slices ===")
for s in samples:
    im = Image.open(s)
    print(f"  {s.name}: size={im.size}, mode={im.mode}")

# New extracted CT variants (negative patients)
new_mid = Path("/root/autodl-tmp/data/bimcv_ct_variants/bimcv_ct_mid")
new_3s = Path("/root/autodl-tmp/data/bimcv_ct_variants/bimcv_ct_3slice")
new_proj = Path("/root/autodl-tmp/data/bimcv_ct_variants/bimcv_ct_proj")
samples_new = sorted(new_mid.glob("bimcv_S*.png"))[:3]
print("=== New negative CT mid variants ===")
for s in samples_new:
    im = Image.open(s)
    print(f"  {s.name}: size={im.size}, mode={im.mode}")
    # Check 3slice
    s3 = new_3s / s.name
    if s3.exists():
        im3 = Image.open(s3)
        print(f"    3slice: size={im3.size}, mode={im3.mode}")
    # Check proj
    sp = new_proj / s.name
    if sp.exists():
        imp = Image.open(sp)
        print(f"    proj: size={imp.size}, mode={imp.mode}")
