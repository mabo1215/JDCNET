from __future__ import annotations

import argparse
import collections
import io
import json
import random
import traceback
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
import pydicom
from pydicom.pixel_data_handlers.util import apply_voi_lut


XRAY_MODALITIES = ("DX", "CR", "DR", "RG")
CHEST_TOKENS = ("CHEST", "THORAX", "LUNG")


def normalize_to_u8(array: np.ndarray, low: float | None = None, high: float | None = None) -> np.ndarray:
    values = np.asarray(array, dtype=np.float32)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    if low is None or high is None:
        low, high = np.percentile(values, [1, 99])
    if high <= low:
        high = low + 1.0
    values = np.clip((values - low) / (high - low), 0.0, 1.0)
    return (values * 255).astype(np.uint8)


def save_grayscale_png(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).convert("L").save(path)


def dicom_sort_key(dataset: Any, fallback: int) -> float:
    image_position = getattr(dataset, "ImagePositionPatient", None)
    if image_position is not None and len(image_position) >= 3:
        try:
            return float(image_position[2])
        except Exception:
            pass
    try:
        return float(getattr(dataset, "InstanceNumber"))
    except Exception:
        return float(fallback)


def read_dicom_bytes_from_zip(zip_file: zipfile.ZipFile, info: zipfile.ZipInfo) -> Any:
    with zip_file.open(info) as handle:
        return pydicom.dcmread(io.BytesIO(handle.read()), force=True)


def build_zip_map(raw_root: Path) -> dict[tuple[str, str], Path]:
    mapping: dict[tuple[str, str], Path] = {}
    for zip_path in raw_root.rglob("*.zip"):
        parts = zip_path.relative_to(raw_root).as_posix().split("/")
        if len(parts) < 2 or "_" not in parts[1]:
            continue
        object_uuid, case_id = parts[1].split("_", 1)
        mapping[(f"dg.MD1R/{object_uuid}", case_id)] = zip_path
    return mapping


def group_metadata(metadata_json: Path) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, int]]:
    records = json.load(open(metadata_json, encoding="utf-8"))
    by_case: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    labels: dict[str, int] = {}
    for row in records:
        case_id = str(row.get("case_submitter_id", "")).strip()
        modality = str(row.get("selected_modality", "")).strip().upper()
        if not case_id or not modality:
            continue
        by_case[case_id][modality] = row
        labels[case_id] = 1 if str(row.get("covid19_positive", "")).lower() == "yes" else 0
    return by_case, labels


def is_chest_case(case_row: dict[str, dict[str, Any]]) -> bool:
    ct_row = case_row.get("CT")
    if not ct_row:
        return False
    description = str(ct_row.get("study_description", "")).upper()
    return any(token in description for token in CHEST_TOKENS)


def choose_xray_row(case_row: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for modality in XRAY_MODALITIES:
        if modality in case_row:
            return case_row[modality]
    return None


def select_cases(
    by_case: dict[str, dict[str, dict[str, Any]]],
    labels: dict[str, int],
    only_chest: bool,
    negative_multiplier: float,
    max_cases: int | None,
    seed: int,
) -> list[str]:
    eligible: list[str] = []
    for case_id, rows in by_case.items():
        if "CT" not in rows or choose_xray_row(rows) is None:
            continue
        if only_chest and not is_chest_case(rows):
            continue
        eligible.append(case_id)

    positives = sorted([case_id for case_id in eligible if labels.get(case_id) == 1])
    negatives = sorted([case_id for case_id in eligible if labels.get(case_id) == 0])
    rng = random.Random(seed)
    rng.shuffle(positives)
    rng.shuffle(negatives)

    if negative_multiplier > 0:
        target_negatives = int(round(len(positives) * negative_multiplier))
        negatives = negatives[: max(1, min(len(negatives), target_negatives))]

    selected = positives + negatives
    rng.shuffle(selected)
    if max_cases is not None and max_cases > 0:
        selected = selected[:max_cases]
    return selected


def extract_ct_mid_slice(case_id: str, zip_path: Path, output_dir: Path) -> dict[str, Any]:
    output_path = output_dir / "images" / "ct_mid_lung" / f"{case_id}_ct_mid_lung.png"
    if output_path.exists():
        return {"teacher_image_path": str(output_path), "ct_cached": True}

    headers: list[tuple[float, str]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for index, info in enumerate([item for item in archive.infolist() if not item.is_dir()]):
            try:
                with archive.open(info) as handle:
                    dataset = pydicom.dcmread(handle, force=True, stop_before_pixels=True)
                if str(getattr(dataset, "Modality", "")).upper() == "CT":
                    headers.append((dicom_sort_key(dataset, index), info.filename))
            except Exception:
                continue
        headers.sort(key=lambda item: item[0])
        if not headers:
            raise RuntimeError(f"No CT DICOM headers found in {zip_path}")
        selected_name = headers[len(headers) // 2][1]
        with archive.open(selected_name) as handle:
            dataset = pydicom.dcmread(io.BytesIO(handle.read()), force=True)

    pixel_array = dataset.pixel_array.astype(np.float32)
    slope = float(getattr(dataset, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(dataset, "RescaleIntercept", 0.0) or 0.0)
    hu = pixel_array * slope + intercept
    save_grayscale_png(normalize_to_u8(hu, -1350.0, 150.0), output_path)
    return {
        "teacher_image_path": str(output_path),
        "ct_slices": len(headers),
        "ct_mid_shape": list(pixel_array.shape),
    }


def extract_xray(case_id: str, zip_path: Path, output_dir: Path) -> dict[str, Any]:
    output_path = output_dir / "images" / "xray" / f"{case_id}_xray.png"
    if output_path.exists():
        return {"image_path": str(output_path), "xray_cached": True}

    with zipfile.ZipFile(zip_path) as archive:
        candidates = [item for item in archive.infolist() if not item.is_dir()]
        if not candidates:
            raise RuntimeError(f"No DICOM files found in {zip_path}")
        info = max(candidates, key=lambda item: item.file_size)
        dataset = read_dicom_bytes_from_zip(archive, info)

    array = apply_voi_lut(dataset.pixel_array, dataset).astype(np.float32)
    if getattr(dataset, "PhotometricInterpretation", "") == "MONOCHROME1":
        array = array.max() - array
    save_grayscale_png(normalize_to_u8(array), output_path)
    return {
        "image_path": str(output_path),
        "xray_shape": list(array.shape),
        "xray_modality": str(getattr(dataset, "Modality", "")),
    }


def assign_splits(rows: list[dict[str, Any]], train_frac: float, val_frac: float, test_frac: float, seed: int) -> None:
    if abs(train_frac + val_frac + test_frac - 1.0) > 1e-8:
        raise ValueError("train_frac + val_frac + test_frac must equal 1.0")
    rng = random.Random(seed)
    for label in (0, 1):
        indices = [index for index, row in enumerate(rows) if row["label"] == label]
        rng.shuffle(indices)
        total = len(indices)
        n_train = int(round(total * train_frac))
        n_val = int(round(total * val_frac))
        if n_train == 0 and total > 0:
            n_train = 1
        if n_val == 0 and total >= 3:
            n_val = 1
        n_test = max(0, total - n_train - n_val)
        if n_train + n_val + n_test > total:
            n_val = max(0, total - n_train)
        for position, index in enumerate(indices):
            if position < n_train:
                rows[index]["split"] = "train"
            elif position < n_train + n_val:
                rows[index]["split"] = "val"
            else:
                rows[index]["split"] = "test"


def write_manifests(rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> dict[str, str]:
    frame = pd.DataFrame(rows)
    paired_path = output_dir / f"{prefix}_paired_manifest.csv"
    frame.to_csv(paired_path, index=False)

    ct_frame = frame.copy()
    ct_frame["image_path"] = ct_frame["teacher_image_path"]
    ct_frame["modality"] = "ct"
    ct_frame["teacher_modality"] = "ct"
    ct_path = output_dir / f"{prefix}_ct_manifest.csv"
    ct_frame.to_csv(ct_path, index=False)
    return {"paired_manifest": str(paired_path), "ct_manifest": str(ct_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a MIDRC CT/X-ray paired PNG dataset and manifests.")
    parser.add_argument("--metadata-json", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="midrc")
    parser.add_argument("--only-chest", action="store_true")
    parser.add_argument("--negative-multiplier", type=float, default=1.0)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--val-frac", type=float, default=0.3)
    parser.add_argument("--test-frac", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    metadata_json = Path(args.metadata_json)
    raw_root = Path(args.raw_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    by_case, labels = group_metadata(metadata_json)
    zip_map = build_zip_map(raw_root)
    selected_cases = select_cases(
        by_case=by_case,
        labels=labels,
        only_chest=args.only_chest,
        negative_multiplier=args.negative_multiplier,
        max_cases=args.max_cases,
        seed=args.seed,
    )

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case_id in selected_cases:
        case_rows = by_case[case_id]
        ct_row = case_rows["CT"]
        xray_row = choose_xray_row(case_rows)
        if xray_row is None:
            continue
        ct_zip = zip_map.get((str(ct_row["object_id"]), case_id))
        xray_zip = zip_map.get((str(xray_row["object_id"]), case_id))
        if ct_zip is None or xray_zip is None:
            errors.append({"case_id": case_id, "error": "zip_not_found"})
            continue
        try:
            record: dict[str, Any] = {
                "label": int(labels[case_id]),
                "patient_id": case_id,
                "pair_id": f"midrc_{case_id}",
                "modality": "xray",
                "teacher_modality": "ct",
                "finding": "COVID-19" if labels[case_id] == 1 else "non-COVID",
                "teacher_finding": "COVID-19" if labels[case_id] == 1 else "non-COVID",
                "view": "unknown",
                "teacher_view": "axial_mid",
                "offset_gap": ct_row.get("pair_day_gap_abs"),
                "source": "midrc",
                "ct_study_description": ct_row.get("study_description"),
                "xray_study_description": xray_row.get("study_description"),
                "ct_zip": str(ct_zip),
                "xray_zip": str(xray_zip),
            }
            record.update(extract_ct_mid_slice(case_id, ct_zip, output_dir))
            record.update(extract_xray(case_id, xray_zip, output_dir))
            rows.append(record)
            print(f"OK {case_id} label={labels[case_id]}", flush=True)
        except Exception as exc:
            errors.append(
                {
                    "case_id": case_id,
                    "error": repr(exc),
                    "trace": traceback.format_exc()[-2000:],
                }
            )
            print(f"ERR {case_id} {exc}", flush=True)

    assign_splits(rows, args.train_frac, args.val_frac, args.test_frac, args.seed)
    manifest_paths = write_manifests(rows, output_dir, args.prefix)
    frame = pd.DataFrame(rows)
    summary = {
        "selected_cases": len(selected_cases),
        "processed_cases": len(rows),
        "errors": errors,
        "label_counts": frame.groupby("label")["patient_id"].nunique().to_dict() if len(frame) else {},
        "split_label_counts": (
            frame.groupby(["split", "label"])["patient_id"].nunique().unstack(fill_value=0).to_dict()
            if len(frame)
            else {}
        ),
        **manifest_paths,
    }
    summary_path = output_dir / f"{args.prefix}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
