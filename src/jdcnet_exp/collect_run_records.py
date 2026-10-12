"""Collect per-run validation and test metrics into one tidy CSV.

Reads the ``best_metrics.json`` (validation partition, best epoch) and
``test_eval/metrics.json`` (test partition) of every run under the given run
roots and writes one row per run. The output contains derived metrics only.

Usage:
    python -m jdcnet_exp.collect_run_records --runs-dir <dir with run roots> --out src/records/runs510_per_run.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOTS = {
    "bimcv_full_paired_cv_20260516": "stage_a",
    "bimcv_pseudolabel_cv_20260516": "jdcnet_initial",
    "bimcv_pseudolabel_lam15_20260516": "jdcnet_extension_a",
    "bimcv_pseudolabel_soft_20260516": "jdcnet_extension_b",
    "bimcv_contrastive_cv_20260516": "contrastive",
    "bimcv_biomedclip_cv_20260516": "biomedclip_226",
    "bimcv_ct_variants_cv_20260516": "ct_variants_226",
    "bimcv_only_calibration_scan_20260514": "gated_scan_balanced",
}

NAME = re.compile(r"^(?P<prefix>.*?)_?f(?P<fold>\d\d)_s(?P<seed>\d+)_?(?P<suffix>.*)$")
FIELDS = ["balanced_accuracy", "roc_auc", "macro_f1", "recall", "specificity", "accuracy", "brier", "pr_auc"]


def parse(stage: str, name: str) -> dict[str, str]:
    m = NAME.match(name)
    if not m:
        return {}
    prefix, suffix = m.group("prefix").rstrip("_"), m.group("suffix")
    out = {"fold": str(int(m.group("fold"))), "seed": m.group("seed"), "variant": prefix or "-", "method": suffix}
    if stage.startswith("jdcnet"):
        pm = re.match(r"pseudolabel_t(\d{3})_l(\d{3})", suffix)
        out["method"] = "jdcnet"
        out["tau"] = f"{int(pm.group(1)) / 100:.2f}"
        out["lambda"] = f"{int(pm.group(2)) / 100:.1f}"
        out["target"] = "soft_kl" if stage == "jdcnet_extension_b" else "hard"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    runs_dir = Path(args.runs_dir)
    rows = []
    for root, stage in ROOTS.items():
        for run in sorted((runs_dir / root).glob("*")):
            info = parse(stage, run.name)
            if not info:
                continue
            row = {"stage": stage, "run": run.name, **info}
            best = run / "best_metrics.json"
            test = run / "test_eval" / "metrics.json"
            if best.exists():
                b = json.loads(best.read_text())
                row["val_balanced_accuracy"] = b.get("balanced_accuracy")
            if test.exists():
                t = json.loads(test.read_text())
                for f in FIELDS:
                    row[f"test_{f}"] = t.get(f)
                cm = t.get("confusion_matrix")
                if cm:
                    row["test_tn"], row["test_fp"], row["test_fn"], row["test_tp"] = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
            rows.append(row)
    keys = ["stage", "run", "variant", "method", "tau", "lambda", "target", "fold", "seed", "val_balanced_accuracy"]
    keys += [f"test_{f}" for f in FIELDS] + ["test_tn", "test_fp", "test_fn", "test_tp"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
