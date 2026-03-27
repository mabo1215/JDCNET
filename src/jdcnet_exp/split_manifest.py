from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


def _assign_group_split(
    manifest: pd.DataFrame,
    train_fraction: float,
    val_fraction: float,
    seed: int,
) -> pd.DataFrame:
    if abs(train_fraction + val_fraction - 1.0) >= 1e-8:
        raise ValueError("train_fraction + val_fraction must equal 1.0 for two-way split.")

    groups = manifest["patient_id"]
    splitter = GroupShuffleSplit(n_splits=1, train_size=train_fraction, random_state=seed)
    train_indices, val_indices = next(splitter.split(manifest, groups=groups))

    manifest = manifest.copy()
    manifest["split"] = "unassigned"
    manifest.loc[train_indices, "split"] = "train"
    manifest.loc[val_indices, "split"] = "val"
    return manifest


def _assign_train_val_test_split(
    manifest: pd.DataFrame,
    train_fraction: float,
    val_fraction: float,
    test_fraction: float,
    seed: int,
) -> pd.DataFrame:
    if abs(train_fraction + val_fraction + test_fraction - 1.0) >= 1e-8:
        raise ValueError("train_fraction + val_fraction + test_fraction must equal 1.0.")

    groups = manifest["patient_id"]
    outer_splitter = GroupShuffleSplit(
        n_splits=1,
        train_size=train_fraction,
        random_state=seed,
    )
    train_indices, remaining_indices = next(outer_splitter.split(manifest, groups=groups))

    manifest = manifest.copy()
    manifest["split"] = "unassigned"
    manifest.loc[train_indices, "split"] = "train"

    remaining = manifest.iloc[remaining_indices].copy()
    remaining_groups = remaining["patient_id"]
    val_ratio_within_remaining = val_fraction / (val_fraction + test_fraction)
    inner_splitter = GroupShuffleSplit(
        n_splits=1,
        train_size=val_ratio_within_remaining,
        random_state=seed,
    )
    val_inner_indices, test_inner_indices = next(
        inner_splitter.split(remaining, groups=remaining_groups)
    )

    manifest.loc[remaining.iloc[val_inner_indices].index, "split"] = "val"
    manifest.loc[remaining.iloc[test_inner_indices].index, "split"] = "test"
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create patient-level splits for a manifest CSV.")
    parser.add_argument("--input", required=True, help="Input CSV without or with placeholder split column.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--test-frac", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    manifest = pd.read_csv(args.input)
    required_columns = {"image_path", "label", "modality", "patient_id"}
    missing = required_columns - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest is missing required columns: {sorted(missing)}")

    if args.test_frac <= 0:
        split_manifest = _assign_group_split(
            manifest,
            train_fraction=args.train_frac,
            val_fraction=args.val_frac,
            seed=args.seed,
        )
    else:
        split_manifest = _assign_train_val_test_split(
            manifest,
            train_fraction=args.train_frac,
            val_fraction=args.val_frac,
            test_fraction=args.test_frac,
            seed=args.seed,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    split_manifest.to_csv(output_path, index=False)
    print(f"Wrote {output_path}")
