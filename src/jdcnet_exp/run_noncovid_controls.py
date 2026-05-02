"""Category-level cross-source non-COVID control evaluation.

This script evaluates the trained JDCNet resampling-study checkpoints on an
extended validation set that combines:
  - COVID-positive CXR images from the original resampling val split (same-patient)
  - Non-COVID CXR images from an independent source (category-level control)

Results are explicitly labelled as category-level control, not same-patient
paired evidence, consistent with the Limitations section of the paper.

Usage:
  python -m jdcnet_exp.run_noncovid_controls
  python -m jdcnet_exp.run_noncovid_controls --noncovid-cxr-manifest src/data/noncovid_cxr_manifest.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)

from .config import load_config
from .data import _build_transform, _load_rgb_image
from .models import build_model


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"

EXPERIMENT_GROUPS = [
    "student_xray_supervised_resampled",
    "student_xray_cross_modal_plain_distill_resampled",
    "student_xray_cross_modal_attention_transfer_resampled",
    "student_xray_cross_modal_feature_hint_resampled",
    "student_xray_cross_modal_distill_resampled",
]

DISPLAY_NAMES = {
    "student_xray_supervised_resampled": "Student-only X-ray",
    "student_xray_cross_modal_plain_distill_resampled": "Plain cross-modal logit KD",
    "student_xray_cross_modal_attention_transfer_resampled": "Cross-modal attention transfer",
    "student_xray_cross_modal_feature_hint_resampled": "Cross-modal feature hint",
    "student_xray_cross_modal_distill_resampled": "Full JDCNet",
}

NUM_RESAMPLES = 8


def _load_model(config_path: Path, checkpoint_path: Path) -> tuple[object, object, int]:
    config = load_config(config_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(config.model).to(device)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()
    transform = _build_transform(config.model.input_size, is_train=False)
    return model, transform, device


def _infer_images(
    model: object,
    transform: object,
    device: object,
    image_paths: list[str],
) -> np.ndarray:
    probs: list[float] = []
    for path in image_paths:
        try:
            tensor = transform(_load_rgb_image(path)).unsqueeze(0).to(device)
        except Exception:
            probs.append(0.5)
            continue
        with torch.no_grad():
            logits = model(tensor)
            p = torch.softmax(logits, dim=1).cpu().numpy()[0][1]
        probs.append(float(p))
    return np.array(probs)


def _compute_metrics(labels: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    preds = (probs >= 0.5).astype(int)
    tp = int(((preds == 1) & (labels == 1)).sum())
    tn = int(((preds == 0) & (labels == 0)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "accuracy": float(accuracy_score(labels, preds)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, preds)),
        "macro_f1": float(f1_score(labels, preds, average="macro", zero_division=0)),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "pr_auc": float(average_precision_score(labels, probs)) if len(np.unique(labels)) > 1 else 0.0,
        "roc_auc": float(roc_auc_score(labels, probs)) if len(np.unique(labels)) > 1 else 0.5,
        "n_positive": int(labels.sum()),
        "n_negative": int((labels == 0).sum()),
    }


def run_noncovid_controls(
    noncovid_cxr_manifest_path: Path,
    config_dir: Path,
    runs_root: Path,
    resampling_data_dir: Path,
    max_noncovid_per_resample: int,
    seed: int,
) -> list[dict[str, object]]:
    noncovid_manifest = pd.read_csv(noncovid_cxr_manifest_path)
    noncovid_val = noncovid_manifest[noncovid_manifest["split"] == "val"].copy().reset_index(drop=True)

    rng = np.random.default_rng(seed)
    if len(noncovid_val) > max_noncovid_per_resample:
        idx = rng.choice(len(noncovid_val), size=max_noncovid_per_resample, replace=False)
        noncovid_val = noncovid_val.iloc[sorted(idx)].reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for group in EXPERIMENT_GROUPS:
        for resample_idx in range(1, NUM_RESAMPLES + 1):
            suffix = f"r{resample_idx:02d}"
            run_name = f"{group}_{suffix}"
            config_path = config_dir / f"{run_name}.json"
            checkpoint_path = runs_root / run_name / "best.pt"

            if not config_path.exists() or not checkpoint_path.exists():
                print(f"  SKIP {run_name}: config or checkpoint missing")
                continue

            split_manifest_path = resampling_data_dir / f"split_{resample_idx:02d}" / "paired_cross_manifest.csv"
            if not split_manifest_path.exists():
                print(f"  SKIP {run_name}: split manifest missing at {split_manifest_path}")
                continue

            split_manifest = pd.read_csv(split_manifest_path)
            covid_val = split_manifest[
                (split_manifest["split"] == "val") & (split_manifest["label"] == 1)
            ][["image_path", "label"]].copy()

            eval_manifest = pd.concat(
                [
                    covid_val[["image_path", "label"]],
                    noncovid_val[["image_path", "label"]],
                ],
                ignore_index=True,
            )
            labels = eval_manifest["label"].to_numpy(dtype=int)
            image_paths = eval_manifest["image_path"].tolist()

            print(f"  Evaluating {run_name} on {len(covid_val)} COVID + {len(noncovid_val)} non-COVID ...", flush=True)
            model, transform, device = _load_model(config_path, checkpoint_path)
            probs = _infer_images(model, transform, device, image_paths)
            metrics = _compute_metrics(labels, probs)

            rows.append(
                {
                    "experiment_group": group,
                    "display_name": DISPLAY_NAMES[group],
                    "resample_index": resample_idx,
                    "run_name": run_name,
                    "control_type": "category_level_cross_source",
                    **metrics,
                }
            )

    return rows


def _aggregate(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    metric_cols = ["accuracy", "balanced_accuracy", "macro_f1", "sensitivity", "specificity", "pr_auc", "roc_auc"]
    agg_rows = []
    for group in EXPERIMENT_GROUPS:
        sub = frame[frame["experiment_group"] == group]
        if sub.empty:
            continue
        entry: dict[str, object] = {
            "experiment_group": group,
            "display_name": DISPLAY_NAMES[group],
            "n_resamples": int(len(sub)),
        }
        for col in metric_cols:
            vals = sub[col].dropna().values
            entry[f"{col}_mean"] = float(np.mean(vals)) if len(vals) else float("nan")
            entry[f"{col}_std"] = float(np.std(vals, ddof=0)) if len(vals) else float("nan")
        agg_rows.append(entry)
    return pd.DataFrame(agg_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate resampling-study models on category-level non-COVID CXR control."
    )
    parser.add_argument(
        "--noncovid-cxr-manifest",
        default=str(SRC_ROOT / "data" / "noncovid_cxr_manifest.csv"),
    )
    parser.add_argument(
        "--config-dir",
        default=str(SRC_ROOT / "configs" / "generated_covid_resampling"),
    )
    parser.add_argument(
        "--runs-root",
        default=str(SRC_ROOT / "runs" / "covid_resampling"),
    )
    parser.add_argument(
        "--resampling-data-dir",
        default=str(SRC_ROOT / "data" / "covid_resampling"),
    )
    parser.add_argument(
        "--max-noncovid-per-resample",
        type=int,
        default=50,
        help="Cap non-COVID images per resample to limit imbalance dominance.",
    )
    parser.add_argument("--seed", type=int, default=99)
    args = parser.parse_args()

    rows = run_noncovid_controls(
        noncovid_cxr_manifest_path=Path(args.noncovid_cxr_manifest),
        config_dir=Path(args.config_dir),
        runs_root=Path(args.runs_root),
        resampling_data_dir=Path(args.resampling_data_dir),
        max_noncovid_per_resample=args.max_noncovid_per_resample,
        seed=args.seed,
    )

    frame = pd.DataFrame(rows)
    summary = _aggregate(rows)

    results_dir = SRC_ROOT / "results"
    paper_results_dir = ROOT / "paper" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    paper_results_dir.mkdir(parents=True, exist_ok=True)

    raw_path = results_dir / "noncovid_control_raw.csv"
    summary_path = results_dir / "noncovid_control_summary.csv"
    paper_summary_path = paper_results_dir / "noncovid_control_summary.csv"

    frame.to_csv(raw_path, index=False)
    summary.to_csv(summary_path, index=False)
    summary.to_csv(paper_summary_path, index=False)

    report_path = results_dir / "noncovid_control_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "raw_csv": str(raw_path),
                "summary_csv": str(summary_path),
                "paper_summary_csv": str(paper_summary_path),
                "note": (
                    "Category-level cross-source control. COVID positives from paired BIMCV cohort "
                    "(same-patient), non-COVID negatives from chest-xray-pneumonia NORMAL class "
                    "(independent source). Not same-patient paired evidence."
                ),
            },
            f,
            indent=2,
        )

    print(f"\nWrote {summary_path}")
    print(f"Wrote {paper_summary_path}")
    print("\n=== Category-level non-COVID control summary ===")
    print(summary[["display_name", "roc_auc_mean", "roc_auc_std", "specificity_mean", "sensitivity_mean"]].to_string(index=False))


if __name__ == "__main__":
    main()
