"""Download non-COVID CXR and CT datasets from Kaggle for category-level control experiments.

Datasets:
  CXR (NORMAL class only): paultimothymooney/chest-xray-pneumonia
  CT  (Non-Covid + Normal): prashant268/chest-ctscan-images

Usage:
  python -m jdcnet_exp.download_noncovid_datasets --output-dir /mnt/d/work/datasets/CTXRAY
  python -m jdcnet_exp.download_noncovid_datasets --cxr-only
  python -m jdcnet_exp.download_noncovid_datasets --ct-only

Kaggle credentials are read from ~/.kaggle/kaggle.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[2]

DATASETS = {
    "cxr": {
        "ref": "paultimothymooney/chest-xray-pneumonia",
        "alias": "noncovid_cxr",
        "notes": "Chest X-ray dataset; NORMAL class used as non-COVID CXR control.",
    },
    "ct": {
        "ref": "mohamedhanyyy/chest-ctscan-images",
        "alias": "noncovid_ct",
        "notes": "Chest CT scan dataset; normal class (Data/*/normal) used as non-COVID CT control.",
    },
}


def _count_files(directory: Path) -> tuple[int, int]:
    count, total_bytes = 0, 0
    for p in directory.rglob("*"):
        if p.is_file():
            count += 1
            total_bytes += p.stat().st_size
    return count, total_bytes


def _download_dataset(api: KaggleApi, ref: str, target_dir: Path, force: bool) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    is_empty = not any(target_dir.iterdir())
    if not force and not is_empty:
        print(f"  SKIP {ref}: {target_dir} already populated (use --force to redownload)")
        return "skipped"
    print(f"  Downloading {ref} → {target_dir} ...")
    api.dataset_download_files(ref, path=str(target_dir), unzip=True, quiet=False)
    return "downloaded"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download non-COVID CXR and CT datasets from Kaggle."
    )
    parser.add_argument(
        "--output-dir",
        default="/mnt/d/work/datasets/CTXRAY",
        help="Root directory; datasets go into <output-dir>/noncovid_cxr and noncovid_ct.",
    )
    parser.add_argument("--cxr-only", action="store_true", help="Download only the CXR dataset.")
    parser.add_argument("--ct-only", action="store_true", help="Download only the CT dataset.")
    parser.add_argument("--force", action="store_true", help="Redownload even if target is not empty.")
    args = parser.parse_args()

    output_root = Path(args.output_dir)
    keys = []
    if args.cxr_only:
        keys = ["cxr"]
    elif args.ct_only:
        keys = ["ct"]
    else:
        keys = ["cxr", "ct"]

    api = KaggleApi()
    api.authenticate()

    report_rows: list[dict[str, object]] = []
    for key in keys:
        info = DATASETS[key]
        target_dir = output_root / info["alias"]
        status = _download_dataset(api, info["ref"], target_dir, args.force)
        file_count, total_bytes = _count_files(target_dir)
        report_rows.append(
            {
                "key": key,
                "dataset_ref": info["ref"],
                "alias": info["alias"],
                "notes": info["notes"],
                "status": status,
                "target_dir": str(target_dir),
                "file_count": file_count,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / 1e6, 1),
            }
        )
        print(f"  {status.upper()} {info['ref']}: {file_count} files, {total_bytes // 1_000_000} MB")

    report_path = ROOT / "src" / "results" / "noncovid_download_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_rows, f, indent=2)
    print(f"\nWrote report: {report_path}")


if __name__ == "__main__":
    main()
