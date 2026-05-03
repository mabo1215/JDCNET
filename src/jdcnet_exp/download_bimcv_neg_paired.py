"""Download only same-patient CT+CXR paired subjects from BIMCV-COVID19- on Kaggle.

BIMCV-COVID19- is the COVID-negative arm of the BIMCV-COVID19 paired cohort.
Patients in this dataset tested negative for COVID-19 but may have pneumonia or
other thoracic pathologies, making them suitable as label=0 (non-COVID) controls
in a same-patient CT+CXR distillation protocol.

Instead of downloading all parts unconditionally, this script:
  1. Enumerates each part's file listing via the Kaggle API to identify
     subject IDs that have both CT (.nii) and CXR (_cr.png / _dx.png),
     tracking file sizes to select the largest (most complete) CT volume.
  2. Downloads only those subjects' CT and CXR files into a flat output
     directory organised by subject ID.
  3. Writes a JSON report of paired subjects and downloaded files.

Usage:
  # Dry run — enumerate only, do not download:
  python -m jdcnet_exp.download_bimcv_neg_paired --dry-run --output-dir /data/bimcv_neg_paired

  # Full download:
  python -m jdcnet_exp.download_bimcv_neg_paired --output-dir /data/bimcv_neg_paired

  # Single part for testing:
  python -m jdcnet_exp.download_bimcv_neg_paired --parts rafiko1/bimcv-covid19-neg-a-0 --output-dir /tmp/bimcv_neg_test

Kaggle credentials must be configured at ~/.kaggle/kaggle.json.

Note on BIMCV-COVID19- parts:
  The negative cohort is distributed across four Kaggle datasets by rafiko1:
    rafiko1/bimcv-covid19-neg-a-0
    rafiko1/bimcv-covid19-neg-b-0
    rafiko1/bimcv-covid19-neg-c-0
    rafiko1/bimcv-covid19-neg-d-0
  If additional parts are released or if the naming scheme differs, pass them
  explicitly via --parts.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[2]

_API: KaggleApi | None = None

# BIMCV-COVID19- parts on Kaggle (COVID-negative arm).
BIMCV_NEG_PARTS = [
    "rafiko1/bimcv-covid19-neg-a-0",
    "rafiko1/bimcv-covid19-neg-b-0",
    "rafiko1/bimcv-covid19-neg-c-0",
    "rafiko1/bimcv-covid19-neg-d-0",
]

_SUBJECT_RE = re.compile(r"sub-(S\d+)")
_CT_SUFFIX = ("_ct.nii", "_ct.nii.gz")
_CXR_SUFFIX = ("_cr.png", "_dx.png", "_rx.png")


def _get_api() -> KaggleApi:
    global _API
    if _API is None:
        _API = KaggleApi()
        _API.authenticate()
    return _API


def _is_ct(name: str) -> bool:
    return any(name.endswith(s) for s in _CT_SUFFIX)


def _is_cxr(name: str) -> bool:
    return "bp-chest" in name and any(name.endswith(s) for s in _CXR_SUFFIX)


def _enumerate_part(
    dataset_ref: str, max_pages: int = 500
) -> dict[str, dict[str, list[tuple[str, int]]]]:
    """
    Use the Kaggle Python API to list all files in one dataset part.
    Returns {subject_id: {"ct": [(file_path, size_bytes), ...],
                          "cxr": [(file_path, size_bytes), ...]}}.
    """
    api = _get_api()
    subjects: dict[str, dict[str, list[tuple[str, int]]]] = {}
    token: str | None = None

    for _ in range(max_pages):
        resp = api.dataset_list_files(dataset_ref, page_token=token, page_size=200)

        for f in resp.files:
            file_path: str = f.name
            size_bytes: int = f.total_bytes or 0

            m = _SUBJECT_RE.search(file_path)
            if m is None:
                continue
            subject_id = m.group(1)
            entry = subjects.setdefault(subject_id, {"ct": [], "cxr": []})
            basename = file_path.split("/")[-1]

            if _is_ct(basename):
                entry["ct"].append((file_path, size_bytes))
            elif _is_cxr(basename):
                entry["cxr"].append((file_path, size_bytes))

        token = getattr(resp, "nextPageToken", None)
        if not token:
            break

    return subjects


def _paired_subjects(
    subjects: dict[str, dict[str, list[tuple[str, int]]]]
) -> dict[str, dict[str, tuple[str, int]]]:
    """Return only subjects that have at least one CT and one CXR.
    Selects the largest CT file per subject.
    """
    paired: dict[str, dict[str, tuple[str, int]]] = {}
    for subject_id, modalities in subjects.items():
        cts = modalities["ct"]
        cxrs = modalities["cxr"]
        if cts and cxrs:
            best_ct = max(cts, key=lambda x: x[1])
            paired[subject_id] = {
                "ct": best_ct,
                "cxrs": cxrs,  # type: ignore[dict-item]
            }
    return paired


def _download_files(
    dataset_ref: str,
    file_paths: list[str],
    output_dir: Path,
    subject_id: str,
) -> list[Path]:
    """Download a set of files from a Kaggle dataset into subject subdirectories."""
    api = _get_api()
    downloaded: list[Path] = []
    for file_path in file_paths:
        basename = file_path.split("/")[-1]
        if _is_ct(basename):
            dest_dir = output_dir / f"sub-{subject_id}" / "ct"
        else:
            dest_dir = output_dir / f"sub-{subject_id}" / "cxr"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / basename
        if dest.exists():
            print(f"    SKIP (exists): {dest}")
            downloaded.append(dest)
            continue
        try:
            with tempfile.TemporaryDirectory() as tmp:
                api.dataset_download_file(
                    dataset_ref,
                    file_name=file_path,
                    path=tmp,
                    quiet=True,
                )
                tmp_path = Path(tmp) / basename
                # Kaggle may append .zip
                if not tmp_path.exists():
                    tmp_path = Path(tmp) / (basename + ".zip")
                if tmp_path.exists() and tmp_path.suffix == ".zip":
                    with zipfile.ZipFile(tmp_path) as zf:
                        zf.extractall(dest_dir)
                    downloaded.append(dest_dir / basename)
                elif tmp_path.exists():
                    shutil.move(str(tmp_path), str(dest))
                    downloaded.append(dest)
                else:
                    print(f"    WARN: downloaded file not found at {tmp_path}")
        except Exception as exc:
            print(f"    ERROR downloading {file_path}: {exc}")
    return downloaded


def run(
    parts: list[str],
    output_dir: Path,
    dry_run: bool,
    min_ct_bytes: int,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_paired: dict[str, dict] = {}
    report: dict = {"parts": {}, "total_subjects": 0, "downloaded_subjects": []}

    for part_ref in parts:
        print(f"\n=== Enumerating {part_ref} ...")
        subjects = _enumerate_part(part_ref)
        paired = _paired_subjects(subjects)

        # Filter by minimum CT size
        if min_ct_bytes > 0:
            paired = {
                sid: info
                for sid, info in paired.items()
                if info["ct"][1] >= min_ct_bytes
            }

        print(f"  {len(subjects)} subjects enumerated, {len(paired)} have paired CT+CXR")
        report["parts"][part_ref] = {"total": len(subjects), "paired": len(paired)}

        # Merge, avoiding duplicates (subject may appear in multiple parts)
        for sid, info in paired.items():
            if sid not in all_paired:
                all_paired[sid] = {"part": part_ref, **info}

    report["total_subjects"] = len(all_paired)
    print(f"\nTotal unique paired subjects across all parts: {len(all_paired)}")

    if dry_run:
        print("DRY RUN — no files downloaded.")
        report["dry_run"] = True
        return report

    for subject_id, info in sorted(all_paired.items()):
        part_ref = info["part"]
        ct_path = info["ct"][0]
        cxr_paths = [c[0] for c in info["cxrs"]]  # type: ignore[index]
        all_files = [ct_path] + cxr_paths

        print(f"  Downloading sub-{subject_id} from {part_ref} ({len(all_files)} files) ...")
        downloaded = _download_files(part_ref, all_files, output_dir, subject_id)
        if downloaded:
            report["downloaded_subjects"].append(subject_id)

    print(f"\nDownloaded {len(report['downloaded_subjects'])} subjects to {output_dir}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download same-patient CT+CXR paired subjects from BIMCV-COVID19- (negative cohort)."
    )
    parser.add_argument(
        "--output-dir",
        default="/data/bimcv_neg_paired",
        help="Root directory where paired subjects will be written (sub-S*/ct/ and sub-S*/cxr/).",
    )
    parser.add_argument(
        "--parts",
        nargs="+",
        default=BIMCV_NEG_PARTS,
        help="Kaggle dataset references to enumerate. Defaults to all known BIMCV-COVID19- parts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate paired subjects without downloading.",
    )
    parser.add_argument(
        "--min-ct-bytes",
        type=int,
        default=1_000_000,
        help="Minimum CT file size in bytes (default: 1 MB) to skip corrupt/placeholder entries.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report = run(
        parts=args.parts,
        output_dir=output_dir,
        dry_run=args.dry_run,
        min_ct_bytes=args.min_ct_bytes,
    )

    report_path = output_dir / "download_report_neg.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
