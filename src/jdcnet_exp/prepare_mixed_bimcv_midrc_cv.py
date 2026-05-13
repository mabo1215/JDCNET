from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd


def _read_manifest(path: Path, source_name: str, require_existing_paths: bool) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"image_path", "teacher_image_path", "label", "patient_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
    output = frame.copy()
    output["source"] = source_name
    output["label"] = output["label"].astype(int)
    output["patient_id"] = output["patient_id"].astype(str)
    if "modality" not in output.columns:
        output["modality"] = "xray"
    if "teacher_modality" not in output.columns:
        output["teacher_modality"] = "ct"
    if "pair_id" not in output.columns:
        output["pair_id"] = [f"{source_name}_{pid}" for pid in output["patient_id"].astype(str)]
    if require_existing_paths:
        image_exists = output["image_path"].map(lambda value: Path(str(value)).is_file())
        teacher_exists = output["teacher_image_path"].map(lambda value: Path(str(value)).is_file())
        output = output[image_exists & teacher_exists].copy()
    return output


def _representative_patient_rows(frame: pd.DataFrame) -> pd.DataFrame:
    sort_columns = [column for column in ("patient_id", "split", "image_path") if column in frame.columns]
    if sort_columns:
        frame = frame.sort_values(sort_columns)
    rows = []
    for patient_id, group in frame.groupby("patient_id", sort=False):
        label = int(group["label"].max())
        source = str(group["source"].iloc[0])
        row = group[group["label"].astype(int) == label].iloc[0].copy()
        row["patient_id"] = str(patient_id)
        row["label"] = label
        row["source"] = source
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def _balanced_source_patient_index(
    bimcv: pd.DataFrame,
    midrc: pd.DataFrame,
    seed: int,
    include_bimcv_negatives: bool,
) -> pd.DataFrame:
    bimcv_patients = _representative_patient_rows(bimcv)
    midrc_patients = _representative_patient_rows(midrc)

    rng = random.Random(seed)
    selected_parts = []

    bimcv_pos = bimcv_patients[bimcv_patients["label"] == 1].copy()
    bimcv_neg = bimcv_patients[bimcv_patients["label"] == 0].copy()
    selected_parts.append(bimcv_pos)
    if include_bimcv_negatives and not bimcv_pos.empty and not bimcv_neg.empty:
        neg_ids = bimcv_neg["patient_id"].astype(str).tolist()
        rng.shuffle(neg_ids)
        keep_ids = set(neg_ids[: min(len(neg_ids), len(bimcv_pos))])
        selected_parts.append(bimcv_neg[bimcv_neg["patient_id"].astype(str).isin(keep_ids)].copy())

    selected_parts.append(midrc_patients.copy())
    selected = pd.concat(selected_parts, ignore_index=True)
    selected["source_stratum"] = selected["source"].astype(str)
    selected["source_label_stratum"] = (
        selected["source"].astype(str) + "_label" + selected["label"].astype(int).astype(str)
    )
    selected["mixed_role"] = selected["source_label_stratum"]
    selected["is_representative_patient_row"] = True
    selected["index_id"] = [f"mixed_cv_{idx:08d}" for idx in range(len(selected))]
    return selected.reset_index(drop=True)


def _assign_cv_splits(frame: pd.DataFrame, folds: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    assignments: dict[str, int] = {}
    for _, group in frame.groupby("source_label_stratum"):
        patient_ids = group["patient_id"].astype(str).tolist()
        rng.shuffle(patient_ids)
        for index, patient_id in enumerate(patient_ids):
            assignments[patient_id] = index % folds
    return assignments


def _write_fold_manifests(frame: pd.DataFrame, output_dir: Path, prefix: str, folds: int) -> dict[str, Any]:
    fold_reports: dict[str, Any] = {}
    for fold in range(folds):
        fold_dir = output_dir / f"fold_{fold:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        fold_frame = frame.copy()
        fold_frame["split"] = "train"
        fold_frame.loc[fold_frame["cv_fold"] == fold, "split"] = "test"
        fold_frame.loc[fold_frame["cv_fold"] == ((fold + 1) % folds), "split"] = "val"

        paired_path = fold_dir / f"{prefix}_fold{fold:02d}_paired_manifest.csv"
        fold_frame.to_csv(paired_path, index=False)

        ct_frame = fold_frame.copy()
        ct_frame["image_path"] = ct_frame["teacher_image_path"]
        ct_frame["modality"] = "ct"
        ct_frame["teacher_modality"] = "ct"
        ct_path = fold_dir / f"{prefix}_fold{fold:02d}_ct_manifest.csv"
        ct_frame.to_csv(ct_path, index=False)

        fold_reports[str(fold)] = {
            "paired_manifest": str(paired_path.resolve()),
            "ct_manifest": str(ct_path.resolve()),
            "split_label_counts": _split_label_counts(fold_frame),
            "split_source_label_counts": _split_source_label_counts(fold_frame),
        }
    return fold_reports


def _split_label_counts(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    report: dict[str, dict[str, int]] = {}
    for split, group in frame.groupby("split"):
        report[str(split)] = {str(k): int(v) for k, v in group["label"].value_counts().sort_index().to_dict().items()}
    return report


def _split_source_label_counts(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    report: dict[str, dict[str, int]] = {}
    for split, group in frame.groupby("split"):
        counts = group.groupby(["source", "label"])["patient_id"].nunique()
        report[str(split)] = {f"{source}_label{label}": int(value) for (source, label), value in counts.items()}
    return report


def _global_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "patients": int(frame["patient_id"].nunique()),
        "label_counts": {str(k): int(v) for k, v in frame["label"].value_counts().sort_index().to_dict().items()},
        "source_label_counts": {
            f"{source}_label{label}": int(value)
            for (source, label), value in frame.groupby(["source", "label"])["patient_id"].nunique().items()
        },
        "source_strata": sorted(frame["source_stratum"].astype(str).unique().tolist()),
        "source_label_strata": sorted(frame["source_label_stratum"].astype(str).unique().tolist()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare patient-level mixed BIMCV+MIDRC cross-validation manifests with source-stratified fields."
    )
    parser.add_argument("--bimcv-manifest", required=True)
    parser.add_argument("--midrc-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="mixed_bimcv_midrc_cv")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--exclude-bimcv-negatives", action="store_true")
    parser.add_argument(
        "--require-existing-paths",
        action="store_true",
        help="Keep only rows whose student and teacher image paths exist on the current machine.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bimcv = _read_manifest(Path(args.bimcv_manifest), "bimcv", args.require_existing_paths)
    midrc = _read_manifest(Path(args.midrc_manifest), "midrc", args.require_existing_paths)
    patient_index = _balanced_source_patient_index(
        bimcv=bimcv,
        midrc=midrc,
        seed=args.seed,
        include_bimcv_negatives=not args.exclude_bimcv_negatives,
    )
    fold_assignments = _assign_cv_splits(patient_index, folds=args.folds, seed=args.seed)
    patient_index["cv_fold"] = patient_index["patient_id"].map(fold_assignments).astype(int)

    index_path = output_dir / f"{args.prefix}_patient_index.csv"
    patient_index.to_csv(index_path, index=False)
    fold_reports = _write_fold_manifests(patient_index, output_dir, args.prefix, args.folds)

    summary = {
        "patient_index": str(index_path.resolve()),
        "folds": args.folds,
        "seed": args.seed,
        "global": _global_summary(patient_index),
        "fold_reports": fold_reports,
        "design_note": (
            "The default design keeps all MIDRC patients, all BIMCV-positive patients, "
            "and a seeded patient-level sample of BIMCV-negative patients matched to the "
            "number of BIMCV-positive patients. Manifests include source_stratum and "
            "source_label_stratum for source-stratified reporting."
        ),
    }
    summary_path = output_dir / f"{args.prefix}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["global"], indent=2))
    print(f"Wrote patient index: {index_path}")
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
