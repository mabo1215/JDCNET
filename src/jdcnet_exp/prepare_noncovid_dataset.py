"""Build category-level control manifests from non-COVID CXR and CT datasets.

This script scans the downloaded non-COVID data and produces CSV manifests with the
same column schema as the existing COVID manifests.  Because these are NOT same-patient
paired data, teacher_image_path is left empty and the manifest is labelled as a
category-level control (label=0, finding='non-covid').

Output manifests:
  noncovid_cxr_manifest.csv   — NORMAL CXR images only
  noncovid_ct_manifest.csv    — Non-Covid + Normal CT images only
  noncovid_combined_manifest.csv — CXR rows only with empty teacher fields (for inference)

Usage:
  python -m jdcnet_exp.prepare_noncovid_dataset --data-root /mnt/d/work/datasets/CTXRAY
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

_CXR_NORMAL_SUBDIRS = [
    "chest_xray/train/NORMAL",
    "chest_xray/val/NORMAL",
    "chest_xray/test/NORMAL",
]

_CT_NONCOVID_SUBDIRS = [
    "Data/train/normal",
    "Data/test/normal",
    "Data/valid/normal",
]

MANIFEST_COLUMNS = [
    "image_path",
    "teacher_image_path",
    "label",
    "modality",
    "teacher_modality",
    "split",
    "patient_id",
    "finding",
    "teacher_finding",
    "view",
    "teacher_view",
    "offset_gap",
]


def _collect_images(root: Path, subdirs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for sub in subdirs:
        subdir = root / sub
        if not subdir.exists():
            print(f"  WARN: subdir not found: {subdir}")
            continue
        found = [p for p in subdir.rglob("*") if p.suffix.lower() in _IMAGE_EXTENSIONS]
        paths.extend(found)
    return paths


def _patient_id_from_filename(path: Path) -> str:
    """Derive a pseudo patient_id from the filename stem (best effort for non-paired data)."""
    return path.stem


def _assign_splits(
    image_paths: list[Path],
    train_frac: float,
    seed: int,
) -> list[str]:
    rng = random.Random(seed)
    indices = list(range(len(image_paths)))
    rng.shuffle(indices)
    n_train = max(1, int(round(len(indices) * train_frac)))
    train_set = set(indices[:n_train])
    return ["train" if i in train_set else "val" for i in range(len(image_paths))]


def _build_manifest(
    image_paths: list[Path],
    modality: str,
    train_frac: float,
    seed: int,
) -> pd.DataFrame:
    splits = _assign_splits(image_paths, train_frac, seed)
    rows = []
    for path, split in zip(image_paths, splits):
        rows.append(
            {
                "image_path": str(path.resolve()),
                "teacher_image_path": "",
                "label": 0,
                "modality": modality,
                "teacher_modality": "",
                "split": split,
                "patient_id": _patient_id_from_filename(path),
                "finding": "non-covid",
                "teacher_finding": "",
                "view": "unknown",
                "teacher_view": "",
                "offset_gap": None,
            }
        )
    return pd.DataFrame(rows, columns=MANIFEST_COLUMNS)


def _summarize(manifest: pd.DataFrame) -> dict[str, object]:
    return {
        "rows": int(len(manifest)),
        "patients": int(manifest["patient_id"].nunique()),
        "label_0": int((manifest["label"] == 0).sum()),
        "label_1": int((manifest["label"] == 1).sum()),
        "train": int((manifest["split"] == "train").sum()),
        "val": int((manifest["split"] == "val").sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare category-level control manifests from non-COVID CXR and CT data."
    )
    parser.add_argument(
        "--data-root",
        default="/mnt/d/work/datasets/CTXRAY",
        help="Root directory containing noncovid_cxr/ and noncovid_ct/ subdirectories.",
    )
    parser.add_argument("--output-dir", default=str(ROOT / "src" / "data"))
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- CXR NORMAL images ---
    cxr_root = data_root / "noncovid_cxr"
    cxr_images = _collect_images(cxr_root, _CXR_NORMAL_SUBDIRS)
    print(f"Found {len(cxr_images)} non-COVID CXR images")

    cxr_manifest = _build_manifest(cxr_images, modality="xray", train_frac=args.train_frac, seed=args.seed)
    cxr_path = output_dir / "noncovid_cxr_manifest.csv"
    cxr_manifest.to_csv(cxr_path, index=False)
    print(f"Wrote {cxr_path}")

    # --- CT Non-Covid + Normal images ---
    ct_root = data_root / "noncovid_ct"
    ct_images = _collect_images(ct_root, _CT_NONCOVID_SUBDIRS)
    print(f"Found {len(ct_images)} non-COVID CT images")

    ct_manifest = _build_manifest(ct_images, modality="ct", train_frac=args.train_frac, seed=args.seed)
    ct_path = output_dir / "noncovid_ct_manifest.csv"
    ct_manifest.to_csv(ct_path, index=False)
    print(f"Wrote {ct_path}")

    summary = {
        "data_root": str(data_root),
        "noncovid_cxr": _summarize(cxr_manifest),
        "noncovid_ct": _summarize(ct_manifest),
    }
    summary_path = ROOT / "src" / "results" / "noncovid_dataset_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
