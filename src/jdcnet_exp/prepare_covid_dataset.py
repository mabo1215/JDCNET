from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def _normalize_modality(raw_value: str) -> str | None:
    mapping = {"X-ray": "xray", "CT": "ct"}
    return mapping.get(str(raw_value))


def _resolve_image_path(dataset_root: Path, filename: str) -> Path | None:
    candidate = dataset_root / "images" / filename
    if candidate.exists():
        return candidate.resolve()
    return None


def _split_patient_ids(
    patient_labels: pd.Series,
    train_fraction: float,
    seed: int,
) -> dict[str, str]:
    rng = random.Random(seed)
    assignments: dict[str, str] = {}

    for label_value in sorted(patient_labels.unique()):
        patient_ids = patient_labels[patient_labels == label_value].index.astype(str).tolist()
        rng.shuffle(patient_ids)

        if len(patient_ids) <= 1:
            train_ids = patient_ids
        else:
            train_count = int(round(len(patient_ids) * train_fraction))
            train_count = max(1, min(len(patient_ids) - 1, train_count))
            train_ids = patient_ids[:train_count]

        train_id_set = set(train_ids)
        for patient_id in patient_ids:
            assignments[patient_id] = "train" if patient_id in train_id_set else "val"

    return assignments


def _summarize_manifest(manifest: pd.DataFrame) -> dict[str, object]:
    return {
        "rows": int(len(manifest)),
        "patients": int(manifest["patient_id"].nunique()),
        "positives": int((manifest["label"] == 1).sum()),
        "negatives": int((manifest["label"] == 0).sum()),
        "train_rows": int((manifest["split"] == "train").sum()),
        "val_rows": int((manifest["split"] == "val").sum()),
        "train_patients": int(manifest.loc[manifest["split"] == "train", "patient_id"].nunique()),
        "val_patients": int(manifest.loc[manifest["split"] == "val", "patient_id"].nunique()),
    }


def _build_base_dataframe(dataset_root: Path) -> pd.DataFrame:
    metadata_path = dataset_root / "metadata.csv"
    metadata = pd.read_csv(metadata_path)
    metadata["modality"] = metadata["modality"].map(_normalize_modality)
    metadata = metadata[metadata["modality"].isin(["xray", "ct"])].copy()
    metadata = metadata[metadata["finding"].notna()].copy()
    metadata = metadata[metadata["finding"] != "todo"].copy()
    metadata["image_path"] = metadata["filename"].astype(str).apply(
        lambda filename: _resolve_image_path(dataset_root, filename)
    )
    metadata = metadata[metadata["image_path"].notna()].copy()
    metadata["image_path"] = metadata["image_path"].astype(str)
    metadata["patient_id"] = metadata["patientid"].astype(str)
    metadata["label"] = metadata["finding"].str.contains("COVID-19", case=False).astype(int)
    metadata["offset_numeric"] = pd.to_numeric(metadata["offset"], errors="coerce")
    metadata["view"] = metadata["view"].fillna("unknown")
    return metadata


def _assign_splits(frame: pd.DataFrame, train_fraction: float, seed: int) -> pd.DataFrame:
    patient_labels = frame.groupby("patient_id")["label"].max()
    assignments = _split_patient_ids(patient_labels=patient_labels, train_fraction=train_fraction, seed=seed)
    output = frame.copy()
    output["split"] = output["patient_id"].map(assignments)
    return output


def _select_teacher_match(xray_row: pd.Series, ct_rows: pd.DataFrame) -> pd.Series:
    if len(ct_rows) == 1:
        return ct_rows.iloc[0]

    xray_offset = xray_row["offset_numeric"]
    ranked_rows = ct_rows.copy()
    if pd.notna(xray_offset) and ranked_rows["offset_numeric"].notna().any():
        ranked_rows["offset_gap"] = (ranked_rows["offset_numeric"] - xray_offset).abs()
    else:
        ranked_rows["offset_gap"] = 0.0

    ranked_rows = ranked_rows.sort_values(
        by=["offset_gap", "view", "filename"],
        ascending=[True, True, True],
        kind="stable",
    )
    return ranked_rows.iloc[0]


def _build_paired_xray_target(base_frame: pd.DataFrame, train_fraction: float, seed: int) -> pd.DataFrame:
    xray_frame = base_frame[base_frame["modality"] == "xray"].copy()
    ct_frame = base_frame[base_frame["modality"] == "ct"].copy()
    paired_patient_ids = sorted(set(xray_frame["patient_id"]) & set(ct_frame["patient_id"]))
    rows: list[dict[str, object]] = []

    for patient_id in paired_patient_ids:
        patient_xray = xray_frame[xray_frame["patient_id"] == patient_id].copy()
        patient_ct = ct_frame[ct_frame["patient_id"] == patient_id].copy()
        if patient_xray.empty or patient_ct.empty:
            continue

        for _, xray_row in patient_xray.iterrows():
            teacher_row = _select_teacher_match(xray_row=xray_row, ct_rows=patient_ct)
            xray_offset = xray_row["offset_numeric"]
            ct_offset = teacher_row["offset_numeric"]
            offset_gap = None
            if pd.notna(xray_offset) and pd.notna(ct_offset):
                offset_gap = float(abs(xray_offset - ct_offset))
            rows.append(
                {
                    "image_path": xray_row["image_path"],
                    "teacher_image_path": teacher_row["image_path"],
                    "label": int(xray_row["label"]),
                    "modality": "xray",
                    "teacher_modality": "ct",
                    "split": "unassigned",
                    "patient_id": patient_id,
                    "finding": xray_row["finding"],
                    "teacher_finding": teacher_row["finding"],
                    "view": xray_row["view"],
                    "teacher_view": teacher_row["view"],
                    "offset_gap": offset_gap,
                }
            )

    paired_manifest = pd.DataFrame(rows)
    patient_labels = paired_manifest.groupby("patient_id")["label"].max()
    assignments = _split_patient_ids(patient_labels=patient_labels, train_fraction=train_fraction, seed=seed)
    paired_manifest["split"] = paired_manifest["patient_id"].map(assignments)
    return paired_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare manifests from the COVID chest X-ray dataset.")
    parser.add_argument(
        "--dataset-root",
        default=r"D:\source\covid-chestxray-dataset",
        help="Root of the covid-chestxray-dataset repository.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "src" / "data"),
        help="Directory where prepared manifests will be written.",
    )
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_frame = _build_base_dataframe(dataset_root)

    xray_manifest = _assign_splits(
        base_frame[base_frame["modality"] == "xray"][
            ["image_path", "label", "modality", "patient_id", "finding", "view", "offset_numeric"]
        ].copy(),
        train_fraction=args.train_frac,
        seed=args.seed,
    )
    ct_manifest = _assign_splits(
        base_frame[base_frame["modality"] == "ct"][
            ["image_path", "label", "modality", "patient_id", "finding", "view", "offset_numeric"]
        ].copy(),
        train_fraction=args.train_frac,
        seed=args.seed,
    )
    paired_manifest = _build_paired_xray_target(base_frame, train_fraction=args.train_frac, seed=args.seed)

    xray_path = output_dir / "covid_xray_all_manifest.csv"
    ct_path = output_dir / "covid_ct_all_manifest.csv"
    paired_path = output_dir / "covid_paired_xray_target_manifest.csv"
    summary_path = ROOT / "src" / "results" / "covid_dataset_summary.json"

    xray_manifest.to_csv(xray_path, index=False)
    ct_manifest.to_csv(ct_path, index=False)
    paired_manifest.to_csv(paired_path, index=False)

    summary = {
        "dataset_root": str(dataset_root),
        "xray_all": _summarize_manifest(xray_manifest),
        "ct_all": _summarize_manifest(ct_manifest),
        "paired_xray_target": _summarize_manifest(paired_manifest),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(f"Wrote {xray_path}")
    print(f"Wrote {ct_path}")
    print(f"Wrote {paired_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
