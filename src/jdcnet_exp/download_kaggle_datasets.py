from __future__ import annotations

import argparse
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATASETS = [
    {
        "ref": "murtozalikhon/brain-tumor-multimodal-image-ct-and-mri",
        "alias": "brain_tumor_ct_mri",
        "notes": "Contains both CT and MRI images and is used as an automatically downloadable multimodal example set.",
    },
    {
        "ref": "kaggleprollc/covid-19-image-data-collection-ieee",
        "alias": "covid_19_ieee_collection",
        "notes": "Public COVID chest imaging collection that can supplement local dataset discovery.",
    },
]


def _write_json(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _list_downloaded_files(target_dir: Path) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    for path in target_dir.rglob("*"):
        if path.is_file():
            file_count += 1
            total_bytes += path.stat().st_size
    return file_count, total_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description="Download curated Kaggle datasets for JDCNET experiments.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "src" / "data" / "kaggle"),
        help="Directory where Kaggle datasets will be downloaded.",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Optional Kaggle dataset ref such as owner/dataset-slug. Can be passed multiple times.",
    )
    parser.add_argument("--force", action="store_true", help="Redownload even if the target directory is not empty.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()

    requested_refs = args.datasets or [entry["ref"] for entry in DEFAULT_DATASETS]
    default_lookup = {entry["ref"]: entry for entry in DEFAULT_DATASETS}
    report_rows: list[dict[str, object]] = []

    for dataset_ref in requested_refs:
        dataset_info = default_lookup.get(
            dataset_ref,
            {
                "ref": dataset_ref,
                "alias": dataset_ref.split("/")[-1].replace("-", "_"),
                "notes": "User-requested dataset.",
            },
        )
        target_dir = output_dir / dataset_info["alias"]
        target_dir.mkdir(parents=True, exist_ok=True)
        is_empty = not any(target_dir.iterdir())
        status = "skipped"

        if args.force or is_empty:
            api.dataset_download_files(dataset_ref, path=str(target_dir), unzip=True, quiet=False)
            status = "downloaded"

        file_count, total_bytes = _list_downloaded_files(target_dir)
        report_rows.append(
            {
                "dataset_ref": dataset_info["ref"],
                "alias": dataset_info["alias"],
                "notes": dataset_info["notes"],
                "status": status,
                "target_dir": str(target_dir),
                "file_count": file_count,
                "total_bytes": total_bytes,
            }
        )

    report_path = ROOT / "src" / "results" / "kaggle_download_report.json"
    _write_json(report_rows, report_path)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
