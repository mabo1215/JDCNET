"""Prepare same-patient CT+CXR paired manifests from the BIMCV-COVID19+ Kaggle dataset.

BIMCV-COVID19+ follows BIDS naming:
  <root>/covid19_posi/sub-<id>/ses-<id>/mod-rx/
    sub-<id>_ses-<id>_..._bp-chest_vp-<view>_cr.png   <- CXR
    sub-<id>_ses-<id>_..._bp-chest_ct.nii              <- CT volume

This script:
  1. Walks the BIMCV root for patients that have both .nii CT and _cr.png CXR.
  2. Extracts the middle axial slice from each CT volume and saves it as a PNG.
  3. Builds the same paired manifest format used by prepare_covid_dataset.py.

Usage:
  python -m jdcnet_exp.prepare_bimcv_dataset \\
      --bimcv-root /data/bimcv_covid19 \\
      --output-dir src/data/bimcv \\
      --slice-dir /data/bimcv_ct_slices
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]

_SUBJECT_RE = re.compile(r"sub-(S\d+)")
_SESSION_RE = re.compile(r"ses-(E\d+)")


def _extract_subject_id(path: Path) -> str | None:
    m = _SUBJECT_RE.search(path.as_posix())
    return m.group(1) if m else None


def _extract_session_id(path: Path) -> str | None:
    m = _SESSION_RE.search(path.as_posix())
    return m.group(1) if m else None


def _ct_middle_axial_slice(nii_path: Path) -> np.ndarray:
    """Load a NIfTI CT volume and return the middle axial slice as uint8."""
    img = nib.load(str(nii_path))
    data = img.get_fdata()

    # Canonicalize orientation so that axis-2 is the axial (superior-inferior) axis.
    # nibabel's as_closest_canonical reorders to RAS; axis 2 is then S-I.
    canonical = nib.as_closest_canonical(img)
    data = canonical.get_fdata()

    if data.ndim == 4:
        data = data[:, :, :, 0]

    mid = data.shape[2] // 2
    # Use a 5-slice average around the midpoint to reduce noise.
    lo = max(0, mid - 2)
    hi = min(data.shape[2], mid + 3)
    slice_2d = data[:, :, lo:hi].mean(axis=2)

    # Lung window: HU center = -600, width = 1500 → [-1350, 150]
    hu_min, hu_max = -1350.0, 150.0
    clipped = np.clip(slice_2d, hu_min, hu_max)
    normalized = ((clipped - hu_min) / (hu_max - hu_min) * 255).astype(np.uint8)
    return normalized


def _save_slice_png(array_2d: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array_2d).save(str(out_path))


def _scan_bimcv_root(bimcv_root: Path) -> dict[str, dict[str, list[Path]]]:
    """Return {subject_id: {"ct": [...nii paths], "cxr": [...png paths]}}."""
    subjects: dict[str, dict[str, list[Path]]] = {}

    for path in bimcv_root.rglob("*"):
        if not path.is_file():
            continue
        subject_id = _extract_subject_id(path)
        if subject_id is None:
            continue
        entry = subjects.setdefault(subject_id, {"ct": [], "cxr": []})

        name = path.name
        if name.endswith("_ct.nii") or name.endswith("_ct.nii.gz"):
            entry["ct"].append(path)
        # BIMCV uses both CR (computed radiograph) and DX (digital radiograph) CXR variants.
        elif "bp-chest" in name and name.endswith(".png") and (
            name.endswith("_cr.png") or name.endswith("_dx.png") or name.endswith("_rx.png")
        ):
            entry["cxr"].append(path)

    return subjects


def _split_patient_ids(
    patient_labels: pd.Series,
    train_fraction: float,
    seed: int,
) -> dict[str, str]:
    rng = random.Random(seed)
    assignments: dict[str, str] = {}
    for label_value in sorted(patient_labels.unique()):
        ids = patient_labels[patient_labels == label_value].index.astype(str).tolist()
        rng.shuffle(ids)
        n_train = max(1, min(len(ids) - 1, round(len(ids) * train_fraction))) if len(ids) > 1 else len(ids)
        train_set = set(ids[:n_train])
        for pid in ids:
            assignments[pid] = "train" if pid in train_set else "val"
    return assignments


def build_paired_manifest(
    bimcv_root: Path,
    slice_dir: Path,
    train_fraction: float,
    seed: int,
    label: int = 1,
) -> pd.DataFrame:
    subjects = _scan_bimcv_root(bimcv_root)
    rows: list[dict[str, object]] = []

    for subject_id, modalities in sorted(subjects.items()):
        ct_files = modalities["ct"]
        cxr_files = modalities["cxr"]
        if not ct_files or not cxr_files:
            continue

        # Use the largest CT file per subject — it is most likely the full-volume acquisition.
        ct_path = max(ct_files, key=lambda p: p.stat().st_size)
        slice_png = slice_dir / f"{subject_id}_ct_mid.png"
        if not slice_png.exists():
            try:
                arr = _ct_middle_axial_slice(ct_path)
                _save_slice_png(arr, slice_png)
            except Exception as exc:
                print(f"  WARN: failed to extract CT slice for {subject_id}: {exc}")
                continue

        for cxr_path in sorted(cxr_files):
            session_id = _extract_session_id(cxr_path) or "unknown"
            rows.append(
                {
                    "image_path": str(cxr_path.resolve()),
                    "teacher_image_path": str(slice_png.resolve()),
                    "label": label,
                    "modality": "xray",
                    "teacher_modality": "ct",
                    "split": "unassigned",
                    "patient_id": f"bimcv_{subject_id}",
                    "finding": "COVID-19" if label == 1 else "non-COVID",
                    "teacher_finding": "COVID-19" if label == 1 else "non-COVID",
                    "view": "AP",
                    "teacher_view": "Axial",
                    "offset_gap": None,
                    "source": "bimcv",
                    "bimcv_session": session_id,
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    patient_labels = df.groupby("patient_id")["label"].max()
    assignments = _split_patient_ids(patient_labels, train_fraction, seed)
    df["split"] = df["patient_id"].map(assignments)
    return df


def _summarize(df: pd.DataFrame) -> dict[str, object]:
    return {
        "rows": int(len(df)),
        "patients": int(df["patient_id"].nunique()),
        "positives": int((df["label"] == 1).sum()),
        "negatives": int((df["label"] == 0).sum()),
        "train_rows": int((df["split"] == "train").sum()),
        "val_rows": int((df["split"] == "val").sum()),
        "train_patients": int(df.loc[df["split"] == "train", "patient_id"].nunique()),
        "val_patients": int(df.loc[df["split"] == "val", "patient_id"].nunique()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build paired CT+CXR manifest from BIMCV-COVID19+ dataset.")
    parser.add_argument(
        "--bimcv-root",
        required=True,
        help="Root directory of the downloaded BIMCV-COVID19+ dataset (contains sub-S* directories).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "src" / "data" / "bimcv"),
        help="Directory where manifests will be written.",
    )
    parser.add_argument(
        "--slice-dir",
        default=None,
        help="Directory to cache extracted CT axial slices (defaults to output-dir/ct_slices).",
    )
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--merge-with",
        default=None,
        help="Optional path to an existing paired manifest CSV to concatenate with the BIMCV manifest.",
    )
    args = parser.parse_args()

    bimcv_root = Path(args.bimcv_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slice_dir = Path(args.slice_dir) if args.slice_dir else output_dir / "ct_slices"
    slice_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning BIMCV root: {bimcv_root}")
    df = build_paired_manifest(
        bimcv_root=bimcv_root,
        slice_dir=slice_dir,
        train_fraction=args.train_frac,
        seed=args.seed,
        label=1,
    )

    if df.empty:
        print("No same-patient CT+CXR pairs found. Check --bimcv-root path.")
        return

    summary = {"bimcv_paired": _summarize(df)}
    print(f"BIMCV pairs found: {_summarize(df)}")

    if args.merge_with:
        existing = pd.read_csv(args.merge_with)
        existing["source"] = existing.get("source", pd.Series("ieee8023", index=existing.index))
        merged = pd.concat([existing, df], ignore_index=True)
        # Re-assign splits at patient level across the merged set.
        patient_labels = merged.groupby("patient_id")["label"].max()
        assignments = _split_patient_ids(patient_labels, args.train_frac, args.seed)
        merged["split"] = merged["patient_id"].map(assignments)
        summary["merged_paired"] = _summarize(merged)
        merged_path = output_dir / "bimcv_merged_paired_manifest.csv"
        merged.to_csv(merged_path, index=False)
        print(f"Wrote merged manifest: {merged_path} ({len(merged)} rows)")

    bimcv_path = output_dir / "bimcv_paired_manifest.csv"
    df.to_csv(bimcv_path, index=False)
    print(f"Wrote BIMCV manifest: {bimcv_path} ({len(df)} rows)")

    summary_path = ROOT / "src" / "results" / "bimcv_dataset_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
