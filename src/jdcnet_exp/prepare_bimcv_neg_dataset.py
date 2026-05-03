"""Prepare same-patient CT+CXR paired manifests from the BIMCV-COVID19- (negative) dataset.

BIMCV-COVID19- subjects tested negative for COVID-19 but may present with pneumonia
or other thoracic pathologies.  They serve as label=0 (non-COVID) controls in a
same-patient CT+CXR distillation protocol, providing a structurally homogeneous
negative arm to pair with BIMCV-COVID19+ positives.

This script reuses the scanning and slice-extraction logic from prepare_bimcv_dataset.py
but forces label=0 for all subjects.  The output manifest format is identical to
the COVID-positive BIMCV manifest and to the Cohen et al. covid_real manifests.

Usage:
  python -m jdcnet_exp.prepare_bimcv_neg_dataset \\
      --bimcv-root /data/bimcv_neg_paired \\
      --output-dir src/data/bimcv \\
      --slice-dir /data/bimcv_neg_ct_slices

  # Merge with BIMCV-positive manifest to build a combined cohort for E1:
  python -m jdcnet_exp.prepare_bimcv_neg_dataset \\
      --bimcv-root /data/bimcv_neg_paired \\
      --output-dir src/data/bimcv \\
      --merge-with src/data/bimcv/bimcv_paired_manifest.csv

Expected input directory layout (produced by download_bimcv_neg_paired.py):
  <bimcv-root>/sub-<S_ID>/ct/<filename>_ct.nii
  <bimcv-root>/sub-<S_ID>/cxr/<filename>_cr.png

Output manifest columns match prepare_bimcv_dataset.py:
  image_path, teacher_image_path, label, modality, teacher_modality,
  split, patient_id, finding, teacher_finding, view, teacher_view,
  offset_gap, source, bimcv_session
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from jdcnet_exp.prepare_bimcv_dataset import (
    build_paired_manifest,
    _split_patient_ids,
    _summarize,
)

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build paired CT+CXR manifest from BIMCV-COVID19- (negative cohort, label=0)."
        )
    )
    parser.add_argument(
        "--bimcv-root",
        required=True,
        help=(
            "Root directory of the downloaded BIMCV-COVID19- dataset "
            "(contains sub-S*/ct/ and sub-S*/cxr/ directories)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "src" / "data" / "bimcv"),
        help="Directory where manifests will be written.",
    )
    parser.add_argument(
        "--slice-dir",
        default=None,
        help="Directory to cache extracted CT axial slices (defaults to output-dir/neg_ct_slices).",
    )
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--merge-with",
        default=None,
        help=(
            "Optional path to an existing paired manifest CSV (e.g., the BIMCV+ positive manifest) "
            "to concatenate with the negative manifest.  Splits are re-assigned at patient level "
            "across the merged set."
        ),
    )
    args = parser.parse_args()

    bimcv_root = Path(args.bimcv_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slice_dir = (
        Path(args.slice_dir) if args.slice_dir else output_dir / "neg_ct_slices"
    )
    slice_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning BIMCV-COVID19- root: {bimcv_root}")
    df = build_paired_manifest(
        bimcv_root=bimcv_root,
        slice_dir=slice_dir,
        train_fraction=args.train_frac,
        seed=args.seed,
        label=0,  # COVID-negative label
    )

    if df.empty:
        print(
            "No same-patient CT+CXR pairs found in the negative cohort. "
            "Check --bimcv-root path and ensure download_bimcv_neg_paired.py was run first."
        )
        return

    summary: dict[str, object] = {"bimcv_neg_paired": _summarize(df)}
    print(f"BIMCV-COVID19- pairs found: {_summarize(df)}")

    if args.merge_with:
        pos_df = pd.read_csv(args.merge_with)
        merged = pd.concat([pos_df, df], ignore_index=True)
        # Re-assign splits at patient level across the merged positive+negative set.
        patient_labels = merged.groupby("patient_id")["label"].max()
        assignments = _split_patient_ids(patient_labels, args.train_frac, args.seed)
        merged["split"] = merged["patient_id"].map(assignments)
        summary["bimcv_combined"] = _summarize(merged)
        merged_path = output_dir / "bimcv_combined_manifest.csv"
        merged.to_csv(merged_path, index=False)
        print(f"Wrote combined positive+negative manifest: {merged_path} ({len(merged)} rows)")
        print(f"  positives: {int((merged['label'] == 1).sum())}, negatives: {int((merged['label'] == 0).sum())}")

    neg_path = output_dir / "bimcv_neg_manifest.csv"
    df.to_csv(neg_path, index=False)
    print(f"Wrote BIMCV-negative manifest: {neg_path} ({len(df)} rows)")

    summary_path = ROOT / "src" / "results" / "bimcv_neg_dataset_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
