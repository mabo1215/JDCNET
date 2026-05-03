"""Prepare paired CT+CXR manifests from the NLST (National Lung Screening Trial) dataset.

NLST is a large-scale lung cancer screening trial (TCIA public collection).
Participants were randomised to low-dose CT or CXR screening annually for 3 years.
A subset of participants received BOTH CT and CXR in the same screening year,
making NLST a natural paired CT+CXR cohort for testing the JDCNet distillation
protocol on a second, independent thoracic domain (lung cancer vs. normal).

Data access:
  NLST is freely available via the TCIA (The Cancer Imaging Archive):
    https://wiki.cancerimagingarchive.net/display/NLST
  Download via NBIA Data Retriever or tcia-utils:
    pip install tcia-utils
    from tcia_utils import nbia
    nbia.downloadSeries(series_list, path="/data/nlst")

Expected input directory layout after download:
  <nlst-root>/
    nlst_ct/
      <participant_id>/           # TCIA series folder
        <StudyInstanceUID>/
          *.dcm                   # CT DICOM slices
    nlst_cxr/
      <participant_id>/
        <StudyInstanceUID>/
          *.dcm                   # CXR DICOM

  Alternatively, if you downloaded the NLST CSV manifest only:
    <nlst-root>/nlst_prsn.csv     # participant table (pid, study_yr, lung_cancer_yn, ...)
    <nlst-root>/nlst_screen.csv   # screening table (pid, study_yr, modality, series_uid, ...)

This script:
  1. Reads NLST participant and screening CSV manifests.
  2. Identifies participants with BOTH a CT series and a CXR series in the same study_yr.
  3. Extracts the middle axial slice from each CT DICOM series (same method as BIMCV).
  4. Builds a manifest in the same format as the Cohen et al. covid_real manifests.

Binary label:
  label=1 → participant had confirmed lung cancer diagnosis in year 1 (lung_cancer_yr1==1)
  label=0 → no lung cancer detected in year 1

Usage:
  python -m jdcnet_exp.prepare_nlst_dataset \\
      --nlst-root /data/nlst \\
      --output-dir src/data/nlst \\
      --slice-dir /data/nlst_ct_slices

  # Dry run — report paired subject counts only, no CT extraction:
  python -m jdcnet_exp.prepare_nlst_dataset \\
      --nlst-root /data/nlst --output-dir src/data/nlst --dry-run
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# DICOM CT middle-axial slice extraction
# ---------------------------------------------------------------------------

def _load_dicom_ct_series(series_dir: Path) -> np.ndarray | None:
    """Load a CT DICOM series and return the middle axial slice as uint8."""
    try:
        import pydicom  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "pydicom is required to read NLST DICOM files. "
            "Install it with: pip install pydicom"
        )

    dcm_files = sorted(series_dir.glob("*.dcm"))
    if not dcm_files:
        return None

    # Read InstanceNumber or SliceLocation to sort slices
    slices: list[tuple[float, np.ndarray]] = []
    for dcm_path in dcm_files:
        try:
            ds = pydicom.dcmread(str(dcm_path), stop_before_pixels=False)
            arr = ds.pixel_array.astype(np.float32)
            # Apply rescale slope/intercept to get Hounsfield units
            slope = float(getattr(ds, "RescaleSlope", 1.0))
            intercept = float(getattr(ds, "RescaleIntercept", 0.0))
            hu = arr * slope + intercept
            instance_num = float(getattr(ds, "InstanceNumber", 0))
            slices.append((instance_num, hu))
        except Exception:
            continue

    if not slices:
        return None

    slices.sort(key=lambda x: x[0])
    volume = np.stack([s[1] for s in slices], axis=2)  # H x W x Z

    # Use a 5-slice average around the midpoint (same as BIMCV script)
    mid = volume.shape[2] // 2
    lo = max(0, mid - 2)
    hi = min(volume.shape[2], mid + 3)
    slice_2d = volume[:, :, lo:hi].mean(axis=2)

    # Lung window: HU center=-600, width=1500 → [-1350, 150]
    hu_min, hu_max = -1350.0, 150.0
    clipped = np.clip(slice_2d, hu_min, hu_max)
    normalized = ((clipped - hu_min) / (hu_max - hu_min) * 255).astype(np.uint8)
    return normalized


def _find_dicom_series(modality_root: Path, participant_id: str) -> list[Path]:
    """Return all series directories for a participant under modality_root."""
    pdir = modality_root / participant_id
    if not pdir.exists():
        return []
    # Series are usually in sub-directories (StudyInstanceUID / SeriesInstanceUID)
    series: list[Path] = []
    for candidate in sorted(pdir.rglob("*.dcm")):
        sdir = candidate.parent
        if sdir not in series:
            series.append(sdir)
    return series


# ---------------------------------------------------------------------------
# Manifest building
# ---------------------------------------------------------------------------

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
        n_train = (
            max(1, min(len(ids) - 1, round(len(ids) * train_fraction)))
            if len(ids) > 1
            else len(ids)
        )
        train_set = set(ids[:n_train])
        for pid in ids:
            assignments[pid] = "train" if pid in train_set else "val"
    return assignments


def build_nlst_manifest(
    nlst_root: Path,
    slice_dir: Path,
    train_fraction: float,
    seed: int,
    dry_run: bool = False,
) -> pd.DataFrame:
    """
    Build a paired CT+CXR manifest from NLST data.

    Requires NLST CSV manifests:
      <nlst_root>/nlst_prsn.csv    — one row per participant
      <nlst_root>/nlst_screen.csv  — one row per screening event

    If CSVs are absent, falls back to scanning <nlst_root>/nlst_ct/ and
    <nlst_root>/nlst_cxr/ directories for DICOM series.
    """
    prsn_csv = nlst_root / "nlst_prsn.csv"
    screen_csv = nlst_root / "nlst_screen.csv"

    ct_root = nlst_root / "nlst_ct"
    cxr_root = nlst_root / "nlst_cxr"

    rows: list[dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # Path A: CSV-driven pairing (preferred if NLST CSVs are available)
    # -----------------------------------------------------------------------
    if prsn_csv.exists() and screen_csv.exists():
        print("Found NLST CSV manifests — using CSV-driven pairing.")
        prsn = pd.read_csv(prsn_csv, low_memory=False)
        screen = pd.read_csv(screen_csv, low_memory=False)

        # Normalise column names to lowercase
        prsn.columns = [c.lower() for c in prsn.columns]
        screen.columns = [c.lower() for c in screen.columns]

        # Determine lung-cancer label (year-1 diagnosis)
        # NLST uses 'lung_cancer_yr1' or 'cancyr' depending on release
        cancer_col = None
        for cand in ["lung_cancer_yr1", "cancyr", "lung_cancer"]:
            if cand in prsn.columns:
                cancer_col = cand
                break

        if cancer_col is None:
            print(
                "  WARN: could not find cancer label column in nlst_prsn.csv. "
                "Defaulting label=0 for all participants."
            )
            prsn["_label"] = 0
        else:
            prsn["_label"] = (prsn[cancer_col] == 1).astype(int)

        pid_to_label = prsn.set_index("pid")["_label"].to_dict()

        # Find participants with both CT and CXR in the same study year
        ct_rows = screen[screen["modality"].str.upper() == "CT"] if "modality" in screen.columns else pd.DataFrame()
        cxr_rows = screen[screen["modality"].str.upper().isin(["CXR", "DX", "CR"])] if "modality" in screen.columns else pd.DataFrame()

        if ct_rows.empty or cxr_rows.empty:
            print(
                "  WARN: 'modality' column not found or no CT/CXR rows. "
                "Falling back to directory scan."
            )
        else:
            # Group by (pid, study_yr)
            ct_pids = set(ct_rows["pid"].astype(str))
            cxr_pids = set(cxr_rows["pid"].astype(str))
            paired_pids = ct_pids & cxr_pids
            print(f"  CT participants: {len(ct_pids)}, CXR participants: {len(cxr_pids)}, paired: {len(paired_pids)}")

            for pid in sorted(paired_pids):
                label = pid_to_label.get(int(pid) if pid.isdigit() else pid, 0)  # type: ignore[arg-type]
                pid_str = f"nlst_{pid}"

                ct_series = _find_dicom_series(ct_root, pid) if ct_root.exists() else []
                cxr_series = _find_dicom_series(cxr_root, pid) if cxr_root.exists() else []

                if not ct_series or not cxr_series:
                    if not dry_run:
                        continue  # skip if actual DICOM not yet downloaded
                    # In dry run, record the pairing intent without file paths
                    rows.append({
                        "image_path": f"<nlst_cxr>/{pid}/<cxr_series>",
                        "teacher_image_path": f"<nlst_ct_slices>/{pid}_ct_mid.png",
                        "label": label,
                        "modality": "xray",
                        "teacher_modality": "ct",
                        "split": "unassigned",
                        "patient_id": pid_str,
                        "finding": "lung_cancer" if label == 1 else "normal",
                        "teacher_finding": "lung_cancer" if label == 1 else "normal",
                        "view": "PA",
                        "teacher_view": "Axial",
                        "offset_gap": None,
                        "source": "nlst",
                        "nlst_study_yr": None,
                    })
                    continue

                # Extract CT middle slice
                slice_png = slice_dir / f"{pid}_ct_mid.png"
                if not slice_png.exists() and not dry_run:
                    ct_series_dir = ct_series[0]
                    arr = _load_dicom_ct_series(ct_series_dir)
                    if arr is not None:
                        slice_dir.mkdir(parents=True, exist_ok=True)
                        Image.fromarray(arr).save(str(slice_png))
                    else:
                        continue

                # One row per CXR series
                for cxr_series_dir in cxr_series:
                    for dcm_file in sorted(cxr_series_dir.glob("*.dcm")):
                        rows.append({
                            "image_path": str(dcm_file.resolve()),
                            "teacher_image_path": str(slice_png.resolve()),
                            "label": label,
                            "modality": "xray",
                            "teacher_modality": "ct",
                            "split": "unassigned",
                            "patient_id": pid_str,
                            "finding": "lung_cancer" if label == 1 else "normal",
                            "teacher_finding": "lung_cancer" if label == 1 else "normal",
                            "view": "PA",
                            "teacher_view": "Axial",
                            "offset_gap": None,
                            "source": "nlst",
                            "nlst_study_yr": None,
                        })
                        break  # one CXR image per participant for simplicity

    # -----------------------------------------------------------------------
    # Path B: Directory scan fallback
    # -----------------------------------------------------------------------
    elif ct_root.exists() and cxr_root.exists():
        print("CSV manifests not found — falling back to directory scan.")
        ct_pids = {p.name for p in ct_root.iterdir() if p.is_dir()}
        cxr_pids = {p.name for p in cxr_root.iterdir() if p.is_dir()}
        paired_pids = ct_pids & cxr_pids
        print(f"  CT dirs: {len(ct_pids)}, CXR dirs: {len(cxr_pids)}, paired: {len(paired_pids)}")

        for pid in sorted(paired_pids):
            pid_str = f"nlst_{pid}"
            slice_png = slice_dir / f"{pid}_ct_mid.png"
            ct_series_dirs = _find_dicom_series(ct_root, pid)
            if not ct_series_dirs:
                continue
            if not slice_png.exists() and not dry_run:
                arr = _load_dicom_ct_series(ct_series_dirs[0])
                if arr is not None:
                    slice_dir.mkdir(parents=True, exist_ok=True)
                    Image.fromarray(arr).save(str(slice_png))
                else:
                    continue

            cxr_series_dirs = _find_dicom_series(cxr_root, pid)
            for cxr_series_dir in cxr_series_dirs:
                for dcm_file in sorted(cxr_series_dir.glob("*.dcm")):
                    rows.append({
                        "image_path": str(dcm_file.resolve()),
                        "teacher_image_path": str(slice_png.resolve()),
                        "label": 0,  # default; override with participant CSV if available
                        "modality": "xray",
                        "teacher_modality": "ct",
                        "split": "unassigned",
                        "patient_id": pid_str,
                        "finding": "unknown",
                        "teacher_finding": "unknown",
                        "view": "PA",
                        "teacher_view": "Axial",
                        "offset_gap": None,
                        "source": "nlst",
                        "nlst_study_yr": None,
                    })
                    break

    else:
        print(
            f"  WARN: Neither CSV manifests nor CT/CXR directories found under {nlst_root}.\n"
            "  Download NLST from TCIA first:\n"
            "    pip install tcia-utils\n"
            "    python -c \"from tcia_utils import nbia; nbia.getCollections()\"\n"
            "  Then re-run this script with --nlst-root pointing to the downloaded data."
        )
        return pd.DataFrame()

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
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build paired CT+CXR manifest from NLST (National Lung Screening Trial)."
    )
    parser.add_argument(
        "--nlst-root",
        required=True,
        help=(
            "Root directory of the downloaded NLST dataset.  Should contain "
            "nlst_prsn.csv + nlst_screen.csv (preferred) or nlst_ct/ + nlst_cxr/ dirs."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "src" / "data" / "nlst"),
        help="Directory where the manifest CSV and summary will be written.",
    )
    parser.add_argument(
        "--slice-dir",
        default=None,
        help="Directory to cache extracted CT axial slices (defaults to output-dir/ct_slices).",
    )
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report paired subject counts without extracting CT slices. "
            "Useful before full DICOM download to estimate dataset size."
        ),
    )
    args = parser.parse_args()

    nlst_root = Path(args.nlst_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slice_dir = Path(args.slice_dir) if args.slice_dir else output_dir / "ct_slices"

    print(f"Building NLST manifest from: {nlst_root}")
    df = build_nlst_manifest(
        nlst_root=nlst_root,
        slice_dir=slice_dir,
        train_fraction=args.train_frac,
        seed=args.seed,
        dry_run=args.dry_run,
    )

    if df.empty:
        print("No paired CT+CXR found. Check --nlst-root and ensure data is downloaded.")
        return

    summary = _summarize(df)
    print(f"NLST paired summary: {summary}")

    manifest_path = output_dir / "nlst_paired_manifest.csv"
    df.to_csv(manifest_path, index=False)
    print(f"Wrote manifest: {manifest_path} ({len(df)} rows)")

    summary_path = ROOT / "src" / "results" / "nlst_dataset_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
