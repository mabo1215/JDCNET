#!/usr/bin/env python3
"""Check label distribution in generated student manifests."""
import csv
import os
from pathlib import Path
from collections import Counter

man_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv/manifests")
for f in sorted(man_dir.glob("*_student_manifest.csv")):
    with open(f) as fh:
        rows = list(csv.DictReader(fh))
    splits = {}
    for r in rows:
        s = r["split"]
        l = int(r["label"])
        splits.setdefault(s, Counter())[l] += 1
    # Check image existence
    missing = 0
    for r in rows:
        if not os.path.exists(r["image_path"]):
            missing += 1
    print(f"{f.name}: total={len(rows)}, missing_images={missing}")
    for s in sorted(splits):
        print(f"  {s}: {dict(splits[s])}")

# Also check a training log for data loading details
print("\n--- Training log first 30 lines ---")
log = Path("/root/autodl-tmp/logs/bimcv_h800_5fold_cv/3slice_f00_s42_supervised.log")
if log.exists():
    lines = log.read_text().splitlines()
    for line in lines[:30]:
        print(line)
