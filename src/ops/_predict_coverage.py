#!/usr/bin/env python3
"""Predict patient coverage after fixing student manifest generation."""
import csv
import re
from pathlib import Path
from collections import Counter

cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")
ct_root = Path("/root/autodl-tmp/data/bimcv_ct_variants")
variants = {"mid": ct_root / "bimcv_ct_mid", "3slice": ct_root / "bimcv_ct_3slice"}

# Compute common (patients with CT variants for ALL teacher variants)
common = None
for t, vdir in variants.items():
    avail = set()
    for f in vdir.glob("bimcv_S*.png"):
        m = re.search(r"S\d+", f.name)
        if m:
            avail.add(m.group(0))
    common = avail if common is None else common & avail
common = set(common or [])
print(f"Patients with CT variants for ALL teachers: {len(common)}")

# Check per-fold coverage with BOTH CT variant + X-ray check
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    with open(csv_p) as f:
        rows = list(csv.DictReader(f))

    splits = {}
    for r in rows:
        pid = r["patient_id"].replace("bimcv_", "")
        ok = pid in common and Path(r["image_path"]).exists()
        if ok:
            s = r["split"]
            l = int(r["label"])
            splits.setdefault(s, Counter())[l] += 1

    print(f"fold={fold}:")
    for s in sorted(splits):
        print(f"  {s}: {dict(splits[s])}")
