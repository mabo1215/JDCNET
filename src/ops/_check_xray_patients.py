#!/usr/bin/env python3
"""Check per-patient X-ray availability."""
import csv
from pathlib import Path
from collections import defaultdict

cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")

# Use fold 0 as representative (all folds have same patients)
csv_p = cv_dir / "fold_00" / "bimcv_full_paired_fold00_paired_manifest.csv"
with open(csv_p) as f:
    rows = list(csv.DictReader(f))

xray_ok = defaultdict(list)  # pid -> label
xray_miss = defaultdict(list)  # pid -> label
for r in rows:
    pid = r["patient_id"]
    label = int(r["label"])
    if Path(r["image_path"]).exists():
        xray_ok[pid].append(label)
    else:
        xray_miss[pid].append(label)

pos_ok = len([p for p, lbls in xray_ok.items() if lbls[0] == 1])
neg_ok = len([p for p, lbls in xray_ok.items() if lbls[0] == 0])
pos_miss = len([p for p, lbls in xray_miss.items() if lbls[0] == 1])
neg_miss = len([p for p, lbls in xray_miss.items() if lbls[0] == 0])

print(f"Patients with X-ray images:   pos={pos_ok}, neg={neg_ok}, total={pos_ok+neg_ok}")
print(f"Patients without X-ray images: pos={pos_miss}, neg={neg_miss}, total={pos_miss+neg_miss}")

# Check which positive patients have X-ray
pos_with_xray = sorted([p for p, lbls in xray_ok.items() if lbls[0] == 1])
print(f"\nPositive patients with X-ray: {len(pos_with_xray)}")
if pos_with_xray:
    print(f"  sample: {pos_with_xray[:5]}")

# Check which negative patients DON'T have X-ray
neg_without_xray = sorted([p for p, lbls in xray_miss.items() if lbls[0] == 0])
print(f"\nNegative patients without X-ray: {len(neg_without_xray)}")
if neg_without_xray:
    print(f"  sample: {neg_without_xray[:5]}")

# Check what's available in bimcv_paired directory
paired_dir = Path("/root/autodl-tmp/data/bimcv_paired")
avail_dirs = sorted([d.name for d in paired_dir.iterdir() if d.is_dir()]) if paired_dir.exists() else []
print(f"\nbimcv_paired directories: {len(avail_dirs)}")

# Check what's available in bimcv_neg_paired
neg_dir = Path("/root/autodl-tmp/data/bimcv_neg_paired")
neg_avail = sorted([d.name for d in neg_dir.iterdir() if d.is_dir()]) if neg_dir.exists() else []
print(f"bimcv_neg_paired directories: {len(neg_avail)}")

# How many fold patients are in each directory?
pos_in_dir = [p for p in pos_with_xray if f"sub-{p.replace('bimcv_', '')}" in avail_dirs]
print(f"\nPositive patients with X-ray AND in bimcv_paired dir: {len(pos_in_dir)}")
