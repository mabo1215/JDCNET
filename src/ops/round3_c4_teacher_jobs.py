"""Build teacher-prediction jobs on re-rendered CT views (run on the 4x3090 host).

The original teacher manifests point to a RAM-disk cache that no longer exists.
The views were re-rendered with the original script into WORK/ct_views; this
script rewrites the image paths and lists one all-split prediction job per
teacher checkpoint so that gate coverage and teacher calibration can be computed.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

WORK = Path("/data1/jdcnet_round3")
SRC = Path("/data1/midrc/bimcv_full_paired_cv_20260516/manifests")
RUNS = Path("/data1/midrc/runs/bimcv_full_paired_cv_20260516")
REWRITE = {
    "/dev/shm/bimcv_ct_": str(WORK / "ct_views" / "bimcv_ct_"),
    "/dev/shm/bimcv_drr/": "/data/bimcv/drr_cache/",
}

(WORK / "manifests").mkdir(parents=True, exist_ok=True)
jobs, missing = [], 0
for view in ("mid", "3slice", "proj", "drr"):
    for fold in range(5):
        src = SRC / f"{view}_fold{fold:02d}_teacher_manifest.csv"
        frame = pd.read_csv(src)
        for old, new in REWRITE.items():
            frame["image_path"] = frame["image_path"].str.replace(old, new, regex=False)
        exists = frame["image_path"].map(lambda p: Path(p).exists())
        missing += int((~exists).sum())
        dst = WORK / "manifests" / src.name
        frame.to_csv(dst, index=False)
        for seed in (42, 43, 44):
            name = f"{view}_f{fold:02d}_s{seed}_teacher"
            ckpt = RUNS / name / "best.pt"
            if ckpt.exists():
                jobs.append({"job": f"teacher/{name}/all", "checkpoint": str(ckpt), "manifest": str(dst), "split": "",
                             "out": str(WORK / "preds" / "teacher" / f"{name}__all.csv")})
out = WORK / "logs" / "teacher_jobs.csv"
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["job", "checkpoint", "manifest", "split", "out"])
    w.writeheader()
    w.writerows(jobs)
print(f"teacher jobs={len(jobs)} missing_images={missing} -> {out}")
