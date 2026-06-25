#!/usr/bin/env python3
"""Check label distribution in CV fold manifests."""
import csv
from pathlib import Path
from collections import Counter

cv_dir = Path("/root/autodl-tmp/bimcv_cv/bimcv_h800_5fold_cv")
for fold in range(5):
    csv_p = cv_dir / f"fold_{fold:02d}" / f"bimcv_full_paired_fold{fold:02d}_paired_manifest.csv"
    with open(csv_p) as f:
        rows = list(csv.DictReader(f))
    splits = {}
    for r in rows:
        s = r["split"]
        l = int(r["label"])
        splits.setdefault(s, Counter())[l] += 1
    print(f"fold={fold}:")
    for s in sorted(splits):
        print(f"  {s}: {dict(splits[s])}")
    # Count unique patients per split+label
    pat_splits = {}
    for r in rows:
        s = r["split"]
        l = int(r["label"])
        pid = r["patient_id"]
        pat_splits.setdefault(s, {}).setdefault(l, set()).add(pid)
    print(f"  patients:")
    for s in sorted(pat_splits):
        counts = {l: len(pids) for l, pids in pat_splits[s].items()}
        print(f"    {s}: {counts}")
