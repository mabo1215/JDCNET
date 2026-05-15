#!/usr/bin/env python3
"""Extract BIMCV CT teacher variants for same-source CV experiments."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from PIL import Image


def patient_from_text(text: str) -> str | None:
    match = re.search(r"S\d+", str(text))
    return match.group(0) if match else None


def build_nifti_index(roots: list[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in list(root.glob("sub-*/ct/*.nii")) + list(root.glob("sub-*/ct/*.nii.gz")):
            patient = patient_from_text(str(path))
            if patient and patient not in index:
                index[patient] = path
    return index


def load_volume(path: Path) -> tuple[np.ndarray, tuple[float, ...]]:
    image = nib.load(str(path))
    data = np.asarray(image.get_fdata(dtype=np.float32))
    data = np.squeeze(data)
    if data.ndim != 3:
        raise ValueError(f"Expected 3D CT volume, got shape={data.shape} for {path}")
    return data, tuple(float(x) for x in image.header.get_zooms()[:3])


def normalize_hu(array: np.ndarray, low: float = -1000.0, high: float = 400.0) -> np.ndarray:
    array = np.clip(array, low, high)
    array = (array - low) / max(high - low, 1e-6)
    return (array * 255.0).astype(np.uint8)


def resize_gray(array: np.ndarray, size: int) -> Image.Image:
    return Image.fromarray(array, mode="L").resize((size, size), Image.BILINEAR)


def resize_rgb(array: np.ndarray, size: int) -> Image.Image:
    return Image.fromarray(array, mode="RGB").resize((size, size), Image.BILINEAR)


def extract_one(path: Path, output_dirs: dict[str, Path], patient: str, size: int) -> None:
    volume, spacing = load_volume(path)
    z_axis = 2
    z_count = volume.shape[z_axis]
    center = z_count // 2
    z_spacing = spacing[z_axis] if len(spacing) > z_axis and spacing[z_axis] > 0 else 1.0
    gap = max(1, int(round(5.0 / z_spacing)))
    indices = [max(0, center - gap), center, min(z_count - 1, center + gap)]

    mid = normalize_hu(volume[:, :, center])
    resize_gray(mid, size).save(output_dirs["mid"] / f"bimcv_{patient}.png")

    stack = np.stack([normalize_hu(volume[:, :, idx]) for idx in indices], axis=-1)
    resize_rgb(stack, size).save(output_dirs["3slice"] / f"bimcv_{patient}.png")

    proj = normalize_hu(np.mean(np.clip(volume, -1000.0, 400.0), axis=2))
    resize_gray(proj, size).save(output_dirs["proj"] / f"bimcv_{patient}.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv-dir", default="/data1/midrc/bimcv_only_cv_20260514")
    parser.add_argument("--prefix", default="bimcv_only")
    parser.add_argument("--roots", nargs="+", default=["/data/bimcv_paired", "/data/bimcv_neg_paired", "/data1/midrc/bimcv_ct_nifti"])
    parser.add_argument("--drr-dir", default="/dev/shm/bimcv_drr")
    parser.add_argument("--out-root", default="/dev/shm")
    parser.add_argument("--size", type=int, default=224)
    parser.add_argument("--summary", default="/data1/logs/bimcv_ct_variants_cv_20260516/extract_summary.json")
    args = parser.parse_args()

    cv_dir = Path(args.cv_dir)
    patients: set[str] = set()
    for fold in range(5):
        csv_path = cv_dir / f"fold_{fold:02d}" / f"{args.prefix}_fold{fold:02d}_paired_manifest.csv"
        frame = pd.read_csv(csv_path)
        patients.update(str(x).replace("bimcv_", "") for x in frame["patient_id"].unique())

    nifti_index = build_nifti_index([Path(x) for x in args.roots])
    drr_dir = Path(args.drr_dir)
    drr_patients = {patient_from_text(path.name) for path in drr_dir.glob("bimcv_S*.png")}
    drr_patients.discard(None)
    common = sorted(p for p in patients if p in nifti_index and p in drr_patients)

    output_dirs = {
        "mid": Path(args.out_root) / "bimcv_ct_mid",
        "3slice": Path(args.out_root) / "bimcv_ct_3slice",
        "proj": Path(args.out_root) / "bimcv_ct_proj",
    }
    for out in output_dirs.values():
        out.mkdir(parents=True, exist_ok=True)

    errors: list[dict[str, str]] = []
    processed: list[str] = []
    for patient in common:
        expected = [out_dir / f"bimcv_{patient}.png" for out_dir in output_dirs.values()]
        if all(path.exists() and path.stat().st_size > 0 for path in expected):
            processed.append(patient)
            continue
        try:
            extract_one(nifti_index[patient], output_dirs, patient, args.size)
            processed.append(patient)
        except Exception as exc:  # noqa: BLE001
            errors.append({"patient": patient, "path": str(nifti_index[patient]), "error": repr(exc)})

    summary = {
        "requested_patients": len(patients),
        "nifti_covered": len(patients & set(nifti_index)),
        "drr_covered": len(patients & set(drr_patients)),
        "common_covered": len(common),
        "processed": len(processed),
        "missing_nifti": sorted(patients - set(nifti_index)),
        "missing_drr": sorted(patients - set(drr_patients)),
        "errors": errors,
        "output_dirs": {k: str(v) for k, v in output_dirs.items()},
    }
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
