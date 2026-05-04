"""Evaluate whether paired manifests are ready for resampling training.

This utility is designed for no-GPU debugging windows: run it after generating
paired manifests (BIMCV/NLST) to decide whether E1/M2/M10 training should start.

Example:
  python -m jdcnet_exp.data_readiness_gate \
      --manifest src/data/bimcv/bimcv_combined_manifest.csv \
      --dataset-name bimcv_combined \
      --output src/results/bimcv_readiness_gate.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def _summary(df: pd.DataFrame) -> dict[str, Any]:
    split_available = "split" in df.columns
    out: dict[str, Any] = {
        "rows": int(len(df)),
        "patients": int(df["patient_id"].nunique()),
        "positive_rows": int((df["label"] == 1).sum()),
        "negative_rows": int((df["label"] == 0).sum()),
        "positive_patients": int(df.loc[df["label"] == 1, "patient_id"].nunique()),
        "negative_patients": int(df.loc[df["label"] == 0, "patient_id"].nunique()),
        "has_split": split_available,
    }
    if split_available:
        train = df[df["split"] == "train"]
        val = df[df["split"] == "val"]
        out.update(
            {
                "train_rows": int(len(train)),
                "val_rows": int(len(val)),
                "train_patients": int(train["patient_id"].nunique()),
                "val_patients": int(val["patient_id"].nunique()),
                "val_positive_patients": int(
                    val.loc[val["label"] == 1, "patient_id"].nunique()
                ),
                "val_negative_patients": int(
                    val.loc[val["label"] == 0, "patient_id"].nunique()
                ),
            }
        )
    return out


def _estimate_val_patients(count: int, train_frac: float) -> int:
    return max(1, int(math.floor(count * (1.0 - train_frac)))) if count > 0 else 0


def _evaluate(
    info: dict[str, Any],
    min_total_patients: int,
    min_pos_patients: int,
    min_neg_patients: int,
    min_val_neg_patients: int,
    min_val_total_patients: int,
    train_fraction: float,
    target_resamples: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    total_patients = int(info["patients"])
    pos_patients = int(info["positive_patients"])
    neg_patients = int(info["negative_patients"])

    if total_patients < min_total_patients:
        reasons.append(
            f"patients {total_patients} < required {min_total_patients}"
        )
    if pos_patients < min_pos_patients:
        reasons.append(
            f"positive_patients {pos_patients} < required {min_pos_patients}"
        )
    if neg_patients < min_neg_patients:
        reasons.append(
            f"negative_patients {neg_patients} < required {min_neg_patients}"
        )

    if bool(info.get("has_split")):
        val_neg = int(info.get("val_negative_patients", 0))
        val_total = int(info.get("val_patients", 0))
    else:
        val_neg = _estimate_val_patients(neg_patients, train_fraction)
        val_total = _estimate_val_patients(total_patients, train_fraction)

    if val_neg < min_val_neg_patients:
        reasons.append(
            f"estimated_val_negative_patients {val_neg} < required {min_val_neg_patients}"
        )
    if val_total < min_val_total_patients:
        reasons.append(
            f"estimated_val_patients {val_total} < required {min_val_total_patients}"
        )

    if target_resamples >= 30 and neg_patients < 25:
        reasons.append(
            "target_resamples>=30 but negative_patients<25; expected repeated split instability"
        )

    return len(reasons) == 0, reasons


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check whether a paired manifest is ready for E1/M2/M10 training."
    )
    parser.add_argument("--manifest", required=True, help="Path to manifest CSV.")
    parser.add_argument("--dataset-name", default="paired_dataset")
    parser.add_argument(
        "--output",
        default=str(ROOT / "src" / "results" / "data_readiness_gate.json"),
        help="Path to write gate JSON report.",
    )
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--target-resamples", type=int, default=10)
    parser.add_argument("--min-total-patients", type=int, default=50)
    parser.add_argument("--min-pos-patients", type=int, default=20)
    parser.add_argument("--min-neg-patients", type=int, default=20)
    parser.add_argument("--min-val-neg-patients", type=int, default=5)
    parser.add_argument("--min-val-total-patients", type=int, default=20)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    df = pd.read_csv(manifest_path)
    required_cols = {"patient_id", "label"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Manifest missing required columns: {sorted(missing)}")

    info = _summary(df)
    ready, reasons = _evaluate(
        info=info,
        min_total_patients=args.min_total_patients,
        min_pos_patients=args.min_pos_patients,
        min_neg_patients=args.min_neg_patients,
        min_val_neg_patients=args.min_val_neg_patients,
        min_val_total_patients=args.min_val_total_patients,
        train_fraction=args.train_frac,
        target_resamples=args.target_resamples,
    )

    report = {
        "dataset": args.dataset_name,
        "manifest": str(manifest_path.resolve()),
        "target_resamples": args.target_resamples,
        "thresholds": {
            "min_total_patients": args.min_total_patients,
            "min_pos_patients": args.min_pos_patients,
            "min_neg_patients": args.min_neg_patients,
            "min_val_neg_patients": args.min_val_neg_patients,
            "min_val_total_patients": args.min_val_total_patients,
            "train_fraction": args.train_frac,
        },
        "summary": info,
        "ready_for_training": ready,
        "decision": "START_TRAINING" if ready else "HOLD_DATA_EXPANSION",
        "blocking_reasons": reasons,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote readiness report: {out_path}")
    print(f"Decision: {report['decision']}")
    if reasons:
        print("Blocking reasons:")
        for reason in reasons:
            print(f"  - {reason}")


if __name__ == "__main__":
    main()
