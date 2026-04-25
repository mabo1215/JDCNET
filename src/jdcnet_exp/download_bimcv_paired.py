"""Download only same-patient CT+CXR paired subjects from BIMCV-COVID19+ on Kaggle.

Instead of downloading all 430 GB across 10 parts, this script:
  1. Enumerates each part's file listing via the Kaggle CLI to identify
     subject IDs that have both CT (.nii) and CXR (_cr.png / _dx.png),
     tracking file sizes to select the largest (most complete) CT volume.
  2. Downloads only those subjects' CT and CXR files into a flat output
     directory organised by subject ID.
  3. Writes a JSON report of paired subjects and downloaded files.

Usage:
  # Dry run — enumerate only, do not download:
  python -m jdcnet_exp.download_bimcv_paired --dry-run --output-dir /data/bimcv_paired

  # Full download:
  python -m jdcnet_exp.download_bimcv_paired --output-dir /data/bimcv_paired

  # Single part for testing:
  python -m jdcnet_exp.download_bimcv_paired --parts rafiko1/bimcv-covid19-d-0 --output-dir /tmp/bimcv_test

Kaggle credentials must be configured at ~/.kaggle/kaggle.json.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[2]

KAGGLE_BIN = "kaggle"
_API: KaggleApi | None = None


def _get_api() -> KaggleApi:
    global _API
    if _API is None:
        _API = KaggleApi()
        _API.authenticate()
    return _API

BIMCV_PARTS = [
    "rafiko1/bimcv-covid19-a-0",
    "rafiko1/bimcv-covid19-a-1",
    "rafiko1/bimcv-covid19-a2",
    "rafiko1/bimcv-covid19-b-0",
    "rafiko1/bimcv-covid19-b-1",
    "rafiko1/bimcv-covid19-b-2",
    "rafiko1/bimcv-covid19-c-0",
    "rafiko1/bimcv-covid19-c-1",
    "rafiko1/bimcv-covid19-c-2",
    "rafiko1/bimcv-covid19-d-0",
]

_SUBJECT_RE = re.compile(r"sub-(S\d+)")
_CT_SUFFIX = ("_ct.nii", "_ct.nii.gz")
_CXR_SUFFIX = ("_cr.png", "_dx.png", "_rx.png")


def _is_ct(name: str) -> bool:
    return any(name.endswith(s) for s in _CT_SUFFIX)


def _is_cxr(name: str) -> bool:
    return "bp-chest" in name and any(name.endswith(s) for s in _CXR_SUFFIX)


def _enumerate_part(dataset_ref: str, max_pages: int = 500) -> dict[str, dict[str, list[tuple[str, int]]]]:
    """
    Use Kaggle Python API to list all files in one dataset part.
    Returns {subject_id: {"ct": [(file_path, size_bytes), ...],
                          "cxr": [(file_path, size_bytes), ...]}}.
    """
    api = _get_api()
    subjects: dict[str, dict[str, list[tuple[str, int]]]] = {}
    token: str | None = None
    page = 0

    for _ in range(max_pages):
        resp = api.dataset_list_files(dataset_ref, page_token=token, page_size=200)
        page += 1

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

        token = resp.next_page_token or None
        if not token:
            break

    return subjects


def enumerate_all_parts(
    parts: list[str],
) -> dict[str, dict[str, list[tuple[str, str, int]]]]:
    """
    Enumerate all parts and return subjects with both CT and CXR.
    Returns {subject_id: {"ct": [(dataset_ref, file_path, size), ...],
                          "cxr": [(dataset_ref, file_path, size), ...]}}
    Only subjects that appear with both modalities are included.
    """
    all_subjects: dict[str, dict[str, list[tuple[str, str, int]]]] = {}

    for part_ref in parts:
        print(f"  Enumerating {part_ref} ...", flush=True)
        subjects = _enumerate_part(part_ref)
        for subject_id, modalities in subjects.items():
            entry = all_subjects.setdefault(subject_id, {"ct": [], "cxr": []})
            for fp, sz in modalities["ct"]:
                entry["ct"].append((part_ref, fp, sz))
            for fp, sz in modalities["cxr"]:
                entry["cxr"].append((part_ref, fp, sz))

    paired = {
        sid: data
        for sid, data in all_subjects.items()
        if data["ct"] and data["cxr"]
    }
    return paired


def _download_single_file(
    dataset_ref: str,
    remote_file_path: str,
    dest_dir: Path,
) -> Path | None:
    """
    Download one file from Kaggle into dest_dir, unpacking the .zip wrapper
    that Kaggle adds to single-file downloads.
    Returns the local Path to the extracted file, or None on failure.
    Skips download if the target file already exists (resume support).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    basename = Path(remote_file_path).name
    zip_path = dest_dir / (basename + ".zip")
    target = dest_dir / basename

    # Resume: skip if already extracted
    if target.exists() and target.stat().st_size > 0:
        return target

    # Resume: extract if zip already downloaded but not unpacked
    if zip_path.exists() and zip_path.stat().st_size > 0 and not target.exists():
        try:
            with zipfile.ZipFile(zip_path) as z:
                target.write_bytes(z.read(z.namelist()[0]))
            zip_path.unlink()
            return target if target.exists() else None
        except zipfile.BadZipFile:
            print(f"    WARN corrupt zip, re-downloading: {zip_path.name}")
            zip_path.unlink()

    cmd = [
        KAGGLE_BIN, "datasets", "download",
        dataset_ref,
        "--file", remote_file_path,
        "-p", str(dest_dir),
        "--quiet",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    WARN download failed: {result.stderr.strip()[:120]}")
        return None

    if zip_path.exists() and not target.exists():
        try:
            with zipfile.ZipFile(zip_path) as z:
                target.write_bytes(z.read(z.namelist()[0]))
            zip_path.unlink()
        except zipfile.BadZipFile:
            print(f"    WARN corrupt zip after download: {zip_path.name}")
            zip_path.unlink()
    return target if target.exists() else None


def download_paired_subjects(
    output_dir: Path,
    parts: list[str],
    dry_run: bool = False,
) -> None:
    print(f"Enumerating {len(parts)} BIMCV parts to find paired subjects ...")
    paired = enumerate_all_parts(parts)
    print(f"Found {len(paired)} same-patient CT+CXR subjects across all parts.\n")

    report: dict[str, object] = {
        "total_paired_subjects": len(paired),
        "parts_enumerated": parts,
        "subjects": [],
    }
    subjects_list: list[dict[str, object]] = []

    for subject_id in sorted(paired):
        data = paired[subject_id]

        # Select the single largest CT file (most likely the full-volume acquisition).
        best_ct = max(data["ct"], key=lambda x: x[2])
        ct_ref, ct_path, ct_size = best_ct

        # All CXR files for this subject.
        cxr_entries = data["cxr"]

        row: dict[str, object] = {
            "subject_id": subject_id,
            "ct_source": ct_ref,
            "ct_file": ct_path,
            "ct_size_mb": round(ct_size / 1e6, 1),
            "cxr_count": len(cxr_entries),
            "cxr_files": [fp for _, fp, _ in cxr_entries],
            "status": "dry_run" if dry_run else "pending",
        }

        if not dry_run:
            subject_dir = output_dir / f"sub-{subject_id}"

            # Resume: skip subjects already fully downloaded
            ct_basename = Path(ct_path).name
            ct_expected = subject_dir / "ct" / ct_basename
            cxr_count_expected = len(cxr_entries)
            cxr_dir = subject_dir / "cxr"
            existing_cxr = list(cxr_dir.glob("*")) if cxr_dir.exists() else []
            if ct_expected.exists() and len(existing_cxr) >= cxr_count_expected:
                print(f"  SKIP {subject_id}: already downloaded")
                row["ct_local"] = str(ct_expected)
                row["cxr_locals"] = [str(p) for p in existing_cxr]
                row["status"] = "downloaded"
                subjects_list.append(row)
                continue

            ct_local = _download_single_file(ct_ref, ct_path, subject_dir / "ct")
            if ct_local:
                print(f"  CT  {subject_id}: {ct_local.name} ({ct_size // 1_000_000} MB)")
                row["ct_local"] = str(ct_local)
            else:
                row["ct_local"] = None
                row["status"] = "ct_failed"

            cxr_locals = []
            for cxr_ref, cxr_fp, _ in cxr_entries:
                cxr_local = _download_single_file(cxr_ref, cxr_fp, subject_dir / "cxr")
                if cxr_local:
                    cxr_locals.append(str(cxr_local))
                    print(f"  CXR {subject_id}: {cxr_local.name}")
            row["cxr_locals"] = cxr_locals
            if row["status"] == "pending":
                row["status"] = "downloaded"
        else:
            print(
                f"  [dry] {subject_id}: CT {ct_size // 1_000_000} MB ({ct_ref}), "
                f"{len(cxr_entries)} CXR"
            )

        subjects_list.append(row)

    report["subjects"] = subjects_list

    report_path = ROOT / "src" / "results" / "bimcv_download_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote report: {report_path}")
    action = "Would download" if dry_run else "Downloaded"
    print(f"{action} {len(paired)} subjects.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download only same-patient CT+CXR paired subjects from BIMCV-COVID19+."
    )
    parser.add_argument(
        "--output-dir",
        default=r"D:\work\datasets\CTXRAY\bimcv_paired",
        help="Root directory where downloaded subject files will be stored.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate only — report paired subjects without downloading.",
    )
    parser.add_argument(
        "--parts",
        nargs="+",
        default=None,
        metavar="DATASET_REF",
        help="Specific BIMCV part refs to process (default: all 10 parts).",
    )
    args = parser.parse_args()

    download_paired_subjects(
        output_dir=Path(args.output_dir),
        parts=args.parts or BIMCV_PARTS,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
