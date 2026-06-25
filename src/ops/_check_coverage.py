#!/usr/bin/env python3
"""Check patient coverage after fixing positive CT variants."""
import csv
import re
from pathlib import Path

cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")
patients = set()
pos_patients = set()
neg_patients = set()
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    with open(csv_p) as f:
        for row in csv.DictReader(f):
            pid = row["patient_id"].replace("bimcv_", "")
            patients.add(pid)
            if int(row["label"]) == 1:
                pos_patients.add(pid)
            else:
                neg_patients.add(pid)

ct_root = Path("/root/autodl-tmp/data/bimcv_ct_variants")
variants = {"mid": "bimcv_ct_mid", "3slice": "bimcv_ct_3slice", "proj": "bimcv_ct_proj"}
for vname, vdir in variants.items():
    vpath = ct_root / vdir
    avail = {re.search(r"S\d+", f.name).group(0) for f in vpath.glob("bimcv_S*.png") if re.search(r"S\d+", f.name)}
    covered_pos = pos_patients & avail
    covered_neg = neg_patients & avail
    missing_pos = pos_patients - avail
    missing_neg = neg_patients - avail
    print(f"{vname}: total={len(avail)}, pos_covered={len(covered_pos)}/{len(pos_patients)}, neg_covered={len(covered_neg)}/{len(neg_patients)}")
    if missing_pos:
        print(f"  missing positive: {sorted(missing_pos)[:5]}...")
    if missing_neg:
        print(f"  missing negative: {sorted(missing_neg)[:5]}... (total={len(missing_neg)})")

# Check X-ray image availability
print("\n=== X-ray availability ===")
xray_ok = 0
xray_missing = []
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    with open(csv_p) as f:
        for row in csv.DictReader(f):
            if Path(row["image_path"]).exists():
                xray_ok += 1
            else:
                xray_missing.append(row["image_path"])
print(f"X-ray images found: {xray_ok}")
print(f"X-ray images missing: {len(xray_missing)}")
if xray_missing:
    print(f"  sample missing: {xray_missing[:3]}")
