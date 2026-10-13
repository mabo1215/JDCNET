"""Build the per-image prediction job list for the round-3 analyses (run on the 4x3090 host)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

CODE_CFG = Path("/data/JDCNET_git/src/configs")
RUNS = Path("/data1/midrc/runs")
WORK = Path("/data1/jdcnet_round3")
MIDRC = "/data1/midrc/locked_validation/midrc_locked_validation_paired_manifest.csv"

groups = []
for fold in range(5):
    for seed in (42, 43, 44):
        for v in ("mid", "3slice", "proj", "drr"):
            for m in ("supervised", "plain_kd", "gated_kd_thr050"):
                if m == "supervised" and v != "mid":
                    continue  # supervised runs are identical across variants
                name = f"{v}_f{fold:02d}_s{seed}_{m}"
                groups.append(("stage_a", name, CODE_CFG / "bimcv_full_paired_cv_20260516" / f"{name}.json",
                               RUNS / "bimcv_full_paired_cv_20260516" / name / "best.pt"))
for tag in ("bimcv_pseudolabel_cv_20260516", "bimcv_pseudolabel_lam15_20260516", "bimcv_pseudolabel_soft_20260516"):
    for run in sorted((RUNS / tag).glob("*_pseudolabel_*")):
        groups.append((tag, run.name, CODE_CFG / tag / f"{run.name}.json", run / "best.pt"))
for cfg in sorted((WORK / "configs" / "sup128_restarts").glob("sup128_*_r??.json")):
    name = cfg.stem
    groups.append(("sup128_restarts", name, cfg, WORK / "runs" / "sup128_restarts" / name / "best.pt"))

jobs = []
for group, name, cfg, ckpt in groups:
    if not cfg.exists():
        continue
    manifest = json.loads(cfg.read_text())["manifest_path"]
    jobs.append({"job": f"{group}/{name}/test", "checkpoint": str(ckpt), "manifest": manifest, "split": "test",
                 "out": str(WORK / "preds" / group / f"{name}__test.csv")})
    jobs.append({"job": f"{group}/{name}/midrc", "checkpoint": str(ckpt), "manifest": MIDRC, "split": "",
                 "out": str(WORK / "preds" / group / f"{name}__midrc.csv")})
ready = [j for j in jobs if Path(j["checkpoint"]).exists()]
out = WORK / "logs" / "predict_jobs.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["job", "checkpoint", "manifest", "split", "out"])
    w.writeheader()
    w.writerows(ready)
print(f"jobs={len(jobs)} ready={len(ready)} -> {out}")
