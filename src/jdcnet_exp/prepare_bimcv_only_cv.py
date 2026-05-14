from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd


def _path_exists(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    return Path(str(value)).is_file()


def _read_manifest(path: Path, require_existing_paths: bool) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"image_path", "teacher_image_path", "label", "patient_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    output = frame.copy()
    output["label"] = output["label"].astype(int)
    output["patient_id"] = output["patient_id"].astype(str)
    output["image_path"] = output["image_path"].astype(str)
    output["teacher_image_path"] = output["teacher_image_path"].astype(str)
    output["modality"] = "xray"
    output["teacher_modality"] = "ct"
    output["source"] = "bimcv"
    if "pair_id" not in output.columns:
        output["pair_id"] = [f"bimcv_{idx:08d}" for idx in range(len(output))]

    before = len(output)
    if require_existing_paths:
        keep = output["image_path"].map(_path_exists) & output["teacher_image_path"].map(_path_exists)
        output = output[keep].copy()
    output.attrs["dropped_missing_paths"] = before - len(output)
    return output.reset_index(drop=True)


def _representative_patient_rows(frame: pd.DataFrame) -> pd.DataFrame:
    sort_columns = [column for column in ("patient_id", "split", "image_path") if column in frame.columns]
    if sort_columns:
        frame = frame.sort_values(sort_columns)
    rows = []
    for patient_id, group in frame.groupby("patient_id", sort=False):
        label = int(group["label"].max())
        # Prefer a row carrying the patient-level positive label if duplicate rows disagree.
        candidates = group[group["label"].astype(int) == label]
        row = candidates.iloc[0].copy()
        row["patient_id"] = str(patient_id)
        row["label"] = label
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def _select_patients(patient_rows: pd.DataFrame, mode: str, seed: int) -> pd.DataFrame:
    if mode == "full":
        selected = patient_rows.copy()
    elif mode == "balanced":
        positives = patient_rows[patient_rows["label"] == 1].copy()
        negatives = patient_rows[patient_rows["label"] == 0].copy()
        rng = random.Random(seed)
        negative_ids = negatives["patient_id"].astype(str).tolist()
        rng.shuffle(negative_ids)
        keep_negative_ids = set(negative_ids[: min(len(negative_ids), len(positives))])
        selected = pd.concat(
            [
                positives,
                negatives[negatives["patient_id"].astype(str).isin(keep_negative_ids)].copy(),
            ],
            ignore_index=True,
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    selected = selected.copy()
    selected["source_stratum"] = "bimcv"
    selected["source_label_stratum"] = "bimcv_label" + selected["label"].astype(int).astype(str)
    selected["is_representative_patient_row"] = True
    selected["index_id"] = [f"bimcv_only_{idx:08d}" for idx in range(len(selected))]
    return selected.reset_index(drop=True)


def _assign_folds(frame: pd.DataFrame, folds: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    assignments: dict[str, int] = {}
    for label, group in frame.groupby("label"):
        patient_ids = group["patient_id"].astype(str).tolist()
        rng.shuffle(patient_ids)
        for index, patient_id in enumerate(patient_ids):
            assignments[patient_id] = index % folds
    return assignments


def _split_label_counts(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    report: dict[str, dict[str, int]] = {}
    for split, group in frame.groupby("split"):
        report[str(split)] = {
            str(label): int(count)
            for label, count in group["label"].value_counts().sort_index().to_dict().items()
        }
    return report


def _write_fold_manifests(frame: pd.DataFrame, output_dir: Path, prefix: str, folds: int) -> dict[str, Any]:
    fold_reports: dict[str, Any] = {}
    for fold in range(folds):
        fold_dir = output_dir / f"fold_{fold:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)

        fold_frame = frame.copy()
        fold_frame["split"] = "train"
        fold_frame.loc[fold_frame["cv_fold"] == fold, "split"] = "test"
        fold_frame.loc[fold_frame["cv_fold"] == ((fold + 1) % folds), "split"] = "val"
        fold_frame["modality"] = "xray"
        fold_frame["teacher_modality"] = "ct"

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
        }
    return fold_reports


def _global_summary(frame: pd.DataFrame, dropped_missing_paths: int, mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "rows": int(len(frame)),
        "patients": int(frame["patient_id"].nunique()),
        "label_counts": {
            str(label): int(count)
            for label, count in frame["label"].value_counts().sort_index().to_dict().items()
        },
        "dropped_missing_paths": int(dropped_missing_paths),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare patient-level BIMCV-only cross-validation manifests.")
    parser.add_argument("--bimcv-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="bimcv_only")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--mode", choices=("balanced", "full"), default="balanced")
    parser.add_argument("--require-existing-paths", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = _read_manifest(Path(args.bimcv_manifest), require_existing_paths=args.require_existing_paths)
    dropped_missing_paths = int(manifest.attrs.get("dropped_missing_paths", 0))
    patient_rows = _representative_patient_rows(manifest)
    selected = _select_patients(patient_rows, mode=args.mode, seed=args.seed)
    assignments = _assign_folds(selected, folds=args.folds, seed=args.seed)
    selected["cv_fold"] = selected["patient_id"].map(assignments).astype(int)

    index_path = output_dir / f"{args.prefix}_patient_index.csv"
    selected.to_csv(index_path, index=False)
    fold_reports = _write_fold_manifests(selected, output_dir, args.prefix, args.folds)

    summary = {
        "patient_index": str(index_path.resolve()),
        "folds": int(args.folds),
        "seed": int(args.seed),
        "global": _global_summary(selected, dropped_missing_paths=dropped_missing_paths, mode=args.mode),
        "fold_reports": fold_reports,
    }
    summary_path = output_dir / f"{args.prefix}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["global"], indent=2))
    print(f"Wrote patient index: {index_path}")
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
