from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SPLIT_SEED_OFFSETS = {"train": 101, "val": 202, "test": 303}


def _nested_get(payload: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    value: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _recipe_default(recipe: dict[str, Any], key: str, default: Any, *aliases: str) -> Any:
    for candidate in (key, *aliases):
        value = _nested_get(recipe, candidate, None)
        if value is not None:
            return value
    return default


def _load_recipe(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_manifest_csv(path: Path, source_name: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"image_path", "label", "patient_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    output = frame.copy()
    output["label"] = output["label"].astype(int)
    output["patient_id"] = output["patient_id"].astype(str)
    output["image_path"] = output["image_path"].astype(str)

    if "teacher_image_path" not in output.columns:
        output["teacher_image_path"] = output["image_path"]
    else:
        output["teacher_image_path"] = output["teacher_image_path"].fillna(output["image_path"]).astype(str)

    if "modality" not in output.columns:
        output["modality"] = "xray"

    output["source"] = source_name
    if "pair_id" not in output.columns:
        output["pair_id"] = [
            f"{source_name}_{patient_id}_{row_index:06d}"
            for row_index, patient_id in enumerate(output["patient_id"].astype(str).tolist())
        ]
    return output


def _midrc_case_rows_from_metadata(metadata_path: Path, midrc_root: Path) -> pd.DataFrame:
    with open(metadata_path, "r", encoding="utf-8") as handle:
        records = json.load(handle)

    grouped: dict[str, dict[str, dict[str, object]]] = {}
    for row in records:
        case_id = str(row.get("case_submitter_id", "")).strip()
        if not case_id:
            continue

        modalities = [str(x).upper() for x in row.get("study_modality", [])]
        if "CT" in modalities:
            modality_key = "ct"
        elif "CR" in modalities or "DX" in modalities:
            modality_key = "xray"
        else:
            continue

        case_bucket = grouped.setdefault(case_id, {})
        file_rel = str(row.get("file_name", "")).strip()
        object_id = str(row.get("object_id", "")).strip()
        if not file_rel:
            continue

        # gen3 combined downloads store files under:
        #   <midrc_root>/<object_id>_<case_submitter_id>/<original file_name without case prefix>
        # where object_id looks like "dg.MD1R/<uuid>".
        rel_parts = file_rel.split("/", 1)
        case_prefix = rel_parts[0] if rel_parts else ""
        tail_rel = rel_parts[1] if len(rel_parts) == 2 else file_rel
        if object_id and case_prefix:
            download_dir = f"{object_id}_{case_prefix}"
            abs_path = (midrc_root / download_dir / tail_rel).resolve()
        else:
            abs_path = (midrc_root / file_rel).resolve()
        candidate = {
            "path": str(abs_path),
            "days_to_study": row.get("days_to_study"),
            "covid19_positive": row.get("covid19_positive", ""),
            "pair_day_gap_abs": row.get("pair_day_gap_abs"),
        }

        existing = case_bucket.get(modality_key)
        if existing is None:
            case_bucket[modality_key] = candidate
            continue

        old_days = existing.get("days_to_study")
        new_days = candidate.get("days_to_study")
        try:
            old_abs = abs(float(old_days))
        except (TypeError, ValueError):
            old_abs = float("inf")
        try:
            new_abs = abs(float(new_days))
        except (TypeError, ValueError):
            new_abs = float("inf")
        if new_abs < old_abs:
            case_bucket[modality_key] = candidate

    rows: list[dict[str, object]] = []
    for case_id, bucket in grouped.items():
        ct = bucket.get("ct")
        xray = bucket.get("xray")
        if ct is None or xray is None:
            continue

        label_raw = str(xray.get("covid19_positive", "")).strip().lower()
        if label_raw == "yes":
            label = 1
        elif label_raw == "no":
            label = 0
        else:
            continue

        rows.append(
            {
                "image_path": xray["path"],
                "teacher_image_path": ct["path"],
                "label": label,
                "modality": "xray",
                "teacher_modality": "ct",
                "patient_id": f"midrc_{case_id}",
                "pair_id": f"midrc_{case_id}",
                "pair_day_gap_abs": xray.get("pair_day_gap_abs", ct.get("pair_day_gap_abs")),
                "source": "midrc",
            }
        )

    if not rows:
        raise ValueError("No valid CT-Xray pairs were parsed from MIDRC metadata.")

    return pd.DataFrame(rows)


def _stratified_patient_split(
    frame: pd.DataFrame,
    train_frac: float,
    val_frac: float,
    test_frac: float,
    seed: int,
) -> dict[str, str]:
    if abs(train_frac + val_frac + test_frac - 1.0) >= 1e-8:
        raise ValueError("train_frac + val_frac + test_frac must equal 1.0")

    patient_labels = frame.groupby("patient_id")["label"].max().astype(int)
    rng = random.Random(seed)
    assignments: dict[str, str] = {}

    for label_value in (0, 1):
        patient_ids = patient_labels[patient_labels == label_value].index.astype(str).tolist()
        rng.shuffle(patient_ids)
        total = len(patient_ids)
        if total == 0:
            continue

        n_train = int(round(total * train_frac))
        n_val = int(round(total * val_frac))
        n_test = total - n_train - n_val

        if n_train == 0 and total > 0:
            n_train = 1
        if n_val == 0 and total >= 3:
            n_val = 1
        n_test = total - n_train - n_val
        if n_test < 0:
            n_test = 0
            n_val = max(0, total - n_train)

        train_ids = patient_ids[:n_train]
        val_ids = patient_ids[n_train : n_train + n_val]
        test_ids = patient_ids[n_train + n_val :]

        for pid in train_ids:
            assignments[pid] = "train"
        for pid in val_ids:
            assignments[pid] = "val"
        for pid in test_ids:
            assignments[pid] = "test"

    missing = set(frame["patient_id"].astype(str).unique()) - set(assignments)
    for pid in missing:
        assignments[pid] = "train"

    return assignments


def _rebalance_split_by_patient(
    split_frame: pd.DataFrame,
    target_positive_ratio: float,
    sampling_mode: str,
    seed: int,
) -> pd.DataFrame:
    if not (0.0 < target_positive_ratio < 1.0):
        raise ValueError("target_positive_ratio must be in (0, 1)")

    patient_labels = split_frame.groupby("patient_id")["label"].max().astype(int)
    pos_ids = patient_labels[patient_labels == 1].index.tolist()
    neg_ids = patient_labels[patient_labels == 0].index.tolist()
    if not pos_ids or not neg_ids:
        return split_frame

    rng = random.Random(seed)
    n_pos = len(pos_ids)
    n_neg = len(neg_ids)
    current_ratio = n_pos / (n_pos + n_neg)

    if abs(current_ratio - target_positive_ratio) < 1e-6:
        return split_frame

    selected_ids: list[str] = []
    if sampling_mode == "downsample":
        if current_ratio < target_positive_ratio:
            target_neg = int(round(n_pos * (1.0 - target_positive_ratio) / target_positive_ratio))
            target_neg = max(1, min(n_neg, target_neg))
            sampled_neg = rng.sample(neg_ids, target_neg)
            selected_ids = pos_ids + sampled_neg
        else:
            target_pos = int(round(n_neg * target_positive_ratio / (1.0 - target_positive_ratio)))
            target_pos = max(1, min(n_pos, target_pos))
            sampled_pos = rng.sample(pos_ids, target_pos)
            selected_ids = sampled_pos + neg_ids
    else:
        if current_ratio < target_positive_ratio:
            target_pos = int(round(n_neg * target_positive_ratio / (1.0 - target_positive_ratio)))
            target_pos = max(n_pos, target_pos)
            extra = target_pos - n_pos
            sampled_pos = [rng.choice(pos_ids) for _ in range(extra)]
            selected_ids = pos_ids + sampled_pos + neg_ids
        else:
            target_neg = int(round(n_pos * (1.0 - target_positive_ratio) / target_positive_ratio))
            target_neg = max(n_neg, target_neg)
            extra = target_neg - n_neg
            sampled_neg = [rng.choice(neg_ids) for _ in range(extra)]
            selected_ids = pos_ids + neg_ids + sampled_neg

    rows = []
    for k, pid in enumerate(selected_ids):
        patient_rows = split_frame[split_frame["patient_id"] == pid].copy()
        patient_rows["sampling_repeat_id"] = k
        rows.append(patient_rows)

    return pd.concat(rows, ignore_index=True)


def _summary(frame: pd.DataFrame) -> dict[str, object]:
    patient_labels = frame.groupby("patient_id")["label"].max() if not frame.empty else pd.Series(dtype=int)
    positive_rows = int((frame["label"] == 1).sum()) if not frame.empty else 0
    negative_rows = int((frame["label"] == 0).sum()) if not frame.empty else 0
    positive_patients = int((patient_labels == 1).sum()) if not patient_labels.empty else 0
    negative_patients = int((patient_labels == 0).sum()) if not patient_labels.empty else 0
    row_total = positive_rows + negative_rows
    patient_total = positive_patients + negative_patients
    return {
        "rows": int(len(frame)),
        "patients": int(frame["patient_id"].nunique()) if not frame.empty else 0,
        "positive_rows": positive_rows,
        "negative_rows": negative_rows,
        "positive_row_ratio": round(positive_rows / row_total, 6) if row_total else None,
        "positive_patients": positive_patients,
        "negative_patients": negative_patients,
        "positive_patient_ratio": round(positive_patients / patient_total, 6) if patient_total else None,
        "sources": (
            frame["source"].value_counts(dropna=False).to_dict() if "source" in frame.columns and not frame.empty else {}
        ),
    }


def main() -> None:
    bootstrap_parser = argparse.ArgumentParser(add_help=False)
    bootstrap_parser.add_argument("--recipe", default=None, help="Optional JSON recipe with source paths and ratio targets.")
    bootstrap_args, _ = bootstrap_parser.parse_known_args()
    recipe = _load_recipe(bootstrap_args.recipe)

    parser = argparse.ArgumentParser(
        description="Build a mixed BIMCV+MIDRC training manifest with patient-level train/val/test splits and optional class-ratio control.",
        parents=[bootstrap_parser],
    )
    parser.add_argument(
        "--bimcv-manifest",
        default=_recipe_default(recipe, "bimcv_manifest", None, "sources.bimcv_manifest"),
        help="Path to BIMCV paired CSV manifest.",
    )
    parser.add_argument(
        "--midrc-manifest",
        default=_recipe_default(recipe, "midrc_manifest", None, "sources.midrc_manifest"),
        help="Path to MIDRC paired CSV manifest.",
    )
    parser.add_argument(
        "--midrc-metadata-json",
        default=_recipe_default(recipe, "midrc_metadata_json", None, "sources.midrc_metadata_json"),
        help="Optional MIDRC metadata JSON (pair objects) used to build a paired CSV index.",
    )
    parser.add_argument(
        "--midrc-root",
        default=_recipe_default(recipe, "midrc_root", None, "sources.midrc_root"),
        help="Root directory prepended to MIDRC metadata file_name paths.",
    )
    parser.add_argument(
        "--output",
        default=_recipe_default(recipe, "output", None, "outputs.manifest"),
        required=_recipe_default(recipe, "output", None, "outputs.manifest") is None,
        help="Output mixed manifest CSV path.",
    )
    parser.add_argument(
        "--summary-output",
        default=_recipe_default(recipe, "summary_output", None, "outputs.summary"),
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--split-output-dir",
        default=_recipe_default(recipe, "split_output_dir", None, "outputs.split_dir"),
        help="Optional directory for separate train.csv, val.csv, and test.csv files.",
    )
    parser.add_argument("--train-frac", type=float, default=_recipe_default(recipe, "train_frac", 0.7, "split.train_frac"))
    parser.add_argument("--val-frac", type=float, default=_recipe_default(recipe, "val_frac", 0.1, "split.val_frac"))
    parser.add_argument("--test-frac", type=float, default=_recipe_default(recipe, "test_frac", 0.2, "split.test_frac"))
    parser.add_argument("--seed", type=int, default=_recipe_default(recipe, "seed", 42, "split.seed"))
    parser.add_argument(
        "--target-train-positive-ratio",
        type=float,
        default=_recipe_default(recipe, "target_train_positive_ratio", None, "ratios.train_positive"),
    )
    parser.add_argument(
        "--target-val-positive-ratio",
        type=float,
        default=_recipe_default(recipe, "target_val_positive_ratio", None, "ratios.val_positive"),
    )
    parser.add_argument(
        "--target-test-positive-ratio",
        type=float,
        default=_recipe_default(recipe, "target_test_positive_ratio", None, "ratios.test_positive"),
    )
    parser.add_argument(
        "--sampling-mode",
        choices=["upsample", "downsample"],
        default=_recipe_default(recipe, "sampling_mode", "upsample", "ratios.sampling_mode"),
        help="How to reach target positive ratio per split.",
    )
    args = parser.parse_args()

    if not args.bimcv_manifest and not args.midrc_manifest and not args.midrc_metadata_json:
        raise ValueError("At least one of --bimcv-manifest, --midrc-manifest, --midrc-metadata-json must be provided.")

    parts: list[pd.DataFrame] = []
    if args.bimcv_manifest:
        parts.append(_read_manifest_csv(Path(args.bimcv_manifest), source_name="bimcv"))
    if args.midrc_manifest:
        parts.append(_read_manifest_csv(Path(args.midrc_manifest), source_name="midrc"))
    if args.midrc_metadata_json:
        if not args.midrc_root:
            raise ValueError("--midrc-root is required when --midrc-metadata-json is provided.")
        parts.append(
            _midrc_case_rows_from_metadata(
                metadata_path=Path(args.midrc_metadata_json),
                midrc_root=Path(args.midrc_root),
            )
        )

    merged = pd.concat(parts, ignore_index=True)
    merged["patient_id"] = merged["patient_id"].astype(str)
    merged["label"] = merged["label"].astype(int)
    merged["split"] = "unassigned"

    assignments = _stratified_patient_split(
        frame=merged,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        test_frac=args.test_frac,
        seed=args.seed,
    )
    merged["split"] = merged["patient_id"].map(assignments)

    split_targets = {
        "train": args.target_train_positive_ratio,
        "val": args.target_val_positive_ratio,
        "test": args.target_test_positive_ratio,
    }
    balanced_splits: list[pd.DataFrame] = []
    for split_name in ("train", "val", "test"):
        split_frame = merged[merged["split"] == split_name].copy()
        target = split_targets[split_name]
        if target is not None and not split_frame.empty:
            split_frame = _rebalance_split_by_patient(
                split_frame=split_frame,
                target_positive_ratio=float(target),
                sampling_mode=args.sampling_mode,
                seed=args.seed + SPLIT_SEED_OFFSETS[split_name],
            )
        balanced_splits.append(split_frame)

    output = pd.concat(balanced_splits, ignore_index=True)
    output["label"] = output["label"].astype(int)
    if "modality" not in output.columns:
        output["modality"] = "xray"
    else:
        output["modality"] = output["modality"].fillna("xray")
    if "teacher_modality" not in output.columns:
        output["teacher_modality"] = "ct"
    else:
        output["teacher_modality"] = output["teacher_modality"].fillna("ct")
    if "pair_id" not in output.columns:
        output["pair_id"] = [
            f"{source}_{patient_id}_{row_index:06d}"
            for row_index, (source, patient_id) in enumerate(
                zip(output["source"].astype(str), output["patient_id"].astype(str))
            )
        ]
    if "index_id" not in output.columns:
        output.insert(0, "index_id", [f"mixed_{row_index:08d}" for row_index in range(len(output))])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)

    split_manifest_paths: dict[str, str] = {}
    if args.split_output_dir:
        split_output_dir = Path(args.split_output_dir)
        split_output_dir.mkdir(parents=True, exist_ok=True)
        for split_name in ("train", "val", "test"):
            split_path = split_output_dir / f"{split_name}.csv"
            output[output["split"] == split_name].to_csv(split_path, index=False)
            split_manifest_paths[split_name] = str(split_path.resolve())

    split_summaries = {
        split_name: _summary(output[output["split"] == split_name].copy())
        for split_name in ("train", "val", "test")
    }
    report = {
        "output_manifest": str(output_path.resolve()),
        "split_manifests": split_manifest_paths,
        "sampling_mode": args.sampling_mode,
        "target_positive_ratio": split_targets,
        "global": _summary(output),
        "splits": split_summaries,
    }

    if args.summary_output:
        summary_path = Path(args.summary_output)
    else:
        summary_path = ROOT / "src" / "results" / "mixed_bimcv_midrc_manifest_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print(f"Wrote mixed manifest: {output_path}")
    print(f"Wrote summary: {summary_path}")
    print(json.dumps(report["splits"], indent=2))


if __name__ == "__main__":
    main()
