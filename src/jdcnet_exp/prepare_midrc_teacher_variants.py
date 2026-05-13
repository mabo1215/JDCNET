from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
import pydicom


WINDOWS = {
    "lung": (-1350.0, 150.0),
    "mediastinal": (-160.0, 240.0),
    "bone": (-500.0, 1500.0),
}


def normalize_to_u8(array: np.ndarray, low: float, high: float) -> np.ndarray:
    values = np.asarray(array, dtype=np.float32)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    if high <= low:
        high = low + 1.0
    values = np.clip((values - low) / (high - low), 0.0, 1.0)
    return (values * 255).astype(np.uint8)


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


def read_ct_headers(zip_path: Path) -> list[str]:
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
    return [filename for _, filename in headers]


def read_ct_hu(archive: zipfile.ZipFile, filename: str) -> np.ndarray:
    with archive.open(filename) as handle:
        dataset = pydicom.dcmread(io.BytesIO(handle.read()), force=True)
    pixel_array = dataset.pixel_array.astype(np.float32)
    slope = float(getattr(dataset, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(dataset, "RescaleIntercept", 0.0) or 0.0)
    return pixel_array * slope + intercept


def select_even_filenames(filenames: list[str], count: int) -> list[str]:
    if count <= 1:
        return [filenames[len(filenames) // 2]]
    if len(filenames) == 1:
        return [filenames[0] for _ in range(count)]
    positions = np.linspace(0, len(filenames) - 1, count)
    return [filenames[int(round(position))] for position in positions]


def save_rgb(channels: list[np.ndarray], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(channels) == 1:
        image = Image.fromarray(channels[0]).convert("RGB")
    else:
        while len(channels) < 3:
            channels.append(channels[-1])
        image = Image.fromarray(np.stack(channels[:3], axis=-1), mode="RGB")
    image.save(path)


def save_montage(images: list[np.ndarray], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pil_images = [Image.fromarray(image).convert("L") for image in images]
    width, height = pil_images[0].size
    canvas = Image.new("L", (width * len(pil_images), height))
    for index, image in enumerate(pil_images):
        canvas.paste(image, (index * width, 0))
    canvas.convert("RGB").save(path)


def build_variant(case_id: str, zip_path: Path, filenames: list[str], variant: str, output_dir: Path) -> Path:
    variant_dir = output_dir / "images" / variant
    path = variant_dir / f"{case_id}_{variant}.png"
    if path.exists():
        return path

    with zipfile.ZipFile(zip_path) as archive:
        if variant == "ct_3slice_lung_rgb":
            selected = [read_ct_hu(archive, name) for name in select_even_filenames(filenames, 3)]
            channels = [normalize_to_u8(slice_array, *WINDOWS["lung"]) for slice_array in selected]
            save_rgb(channels, path)
        elif variant == "ct_5slice_lung_montage":
            selected = [read_ct_hu(archive, name) for name in select_even_filenames(filenames, 5)]
            images = [normalize_to_u8(slice_array, *WINDOWS["lung"]) for slice_array in selected]
            save_montage(images, path)
        elif variant == "ct_9slice_lung_montage":
            selected = [read_ct_hu(archive, name) for name in select_even_filenames(filenames, 9)]
            images = [normalize_to_u8(slice_array, *WINDOWS["lung"]) for slice_array in selected]
            save_montage(images, path)
        elif variant == "ct_multiwindow_mid_rgb":
            mid_slice = read_ct_hu(archive, filenames[len(filenames) // 2])
            channels = [
                normalize_to_u8(mid_slice, *WINDOWS["lung"]),
                normalize_to_u8(mid_slice, *WINDOWS["mediastinal"]),
                normalize_to_u8(mid_slice, *WINDOWS["bone"]),
            ]
            save_rgb(channels, path)
        elif variant in {"ct_mean_projection_lung", "ct_mip_lung"}:
            projection: np.ndarray | None = None
            count = 0
            for filename in filenames:
                slice_array = read_ct_hu(archive, filename)
                if projection is None:
                    projection = np.zeros_like(slice_array, dtype=np.float32)
                if slice_array.shape != projection.shape:
                    continue
                if variant == "ct_mean_projection_lung":
                    projection += slice_array
                    count += 1
                else:
                    if count == 0:
                        projection = slice_array.copy()
                    else:
                        projection = np.maximum(projection, slice_array)
                    count += 1
            if projection is None or count == 0:
                raise RuntimeError(f"No projection-compatible CT slices found in {zip_path}")
            if variant == "ct_mean_projection_lung":
                projection = projection / float(count)
            save_rgb([normalize_to_u8(projection, *WINDOWS["lung"])], path)
        else:
            raise ValueError(f"Unsupported variant: {variant}")
    return path


def write_variant_manifest(frame: pd.DataFrame, output_dir: Path, prefix: str, variant: str, paths: dict[str, str]) -> str:
    variant_frame = frame.copy()
    variant_frame["teacher_image_path"] = variant_frame["patient_id"].astype(str).map(paths)
    variant_frame["image_path"] = variant_frame["teacher_image_path"]
    variant_frame["modality"] = "ct"
    variant_frame["teacher_modality"] = "ct"
    variant_frame["teacher_view"] = variant
    variant_frame["ct_teacher_variant"] = variant
    manifest_path = output_dir / f"{prefix}_{variant}_ct_manifest.csv"
    variant_frame.to_csv(manifest_path, index=False)
    return str(manifest_path.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare CPU-only MIDRC CT teacher image variants.")
    parser.add_argument("--manifest", required=True, help="MIDRC paired manifest with ct_zip and patient_id columns.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="midrc_teacher_variant")
    parser.add_argument(
        "--variants",
        nargs="+",
        default=[
            "ct_3slice_lung_rgb",
            "ct_5slice_lung_montage",
            "ct_9slice_lung_montage",
            "ct_multiwindow_mid_rgb",
            "ct_mean_projection_lung",
            "ct_mip_lung",
        ],
    )
    args = parser.parse_args()

    frame = pd.read_csv(args.manifest)
    required = {"patient_id", "ct_zip", "label"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{args.manifest} is missing required columns: {sorted(missing)}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    variant_paths: dict[str, dict[str, str]] = {variant: {} for variant in args.variants}
    errors: list[dict[str, str]] = []
    for _, row in frame.drop_duplicates("patient_id").iterrows():
        case_id = str(row["patient_id"])
        try:
            zip_path = Path(str(row["ct_zip"]))
            filenames = read_ct_headers(zip_path)
            for variant in args.variants:
                path = build_variant(case_id, zip_path, filenames, variant, output_dir)
                variant_paths[variant][case_id] = str(path)
            print(f"OK {case_id} slices={len(filenames)}", flush=True)
        except Exception as exc:
            errors.append({"patient_id": case_id, "error": repr(exc)})
            print(f"ERR {case_id} {exc}", flush=True)

    manifests = {
        variant: write_variant_manifest(frame, output_dir, args.prefix, variant, paths)
        for variant, paths in variant_paths.items()
    }
    summary = {
        "input_manifest": str(Path(args.manifest).resolve()),
        "output_dir": str(output_dir.resolve()),
        "variants": args.variants,
        "variant_manifests": manifests,
        "processed_patients": {
            variant: len(paths) for variant, paths in variant_paths.items()
        },
        "errors": errors,
    }
    summary_path = output_dir / f"{args.prefix}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
