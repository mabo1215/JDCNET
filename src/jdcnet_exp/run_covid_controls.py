from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, recall_score

from .config import load_config
from .data import _build_transform, _load_rgb_image
from .models import build_model
from .run_covid_matrix import (
    ROOT,
    SRC_ROOT,
    _aggregate_mean_std,
    _build_config,
    _collect_run_rows,
    _ensure_same_modality_manifest,
    _prepare_dataset,
    _run_training_config,
    _write_config,
)


PAPER_IMAGE_DIR = ROOT / "paper" / "images" / "generated"
PAPER_RESULTS_DIR = ROOT / "paper" / "results"
SRC_RESULTS_DIR = ROOT / "src" / "results"

CONTROL_GROUPS = [
    "student_xray_supervised_paired",
    "student_xray_supervised_paired_balanced",
    "student_xray_cross_modal_plain_distill",
    "student_xray_cross_modal_plain_distill_balanced",
    "student_xray_cross_modal_distill",
    "student_xray_cross_modal_distill_balanced",
]

DISPLAY_NAMES = {
    "student_xray_supervised_paired": "Student-only",
    "student_xray_supervised_paired_balanced": "Student-only + balanced sampler",
    "student_xray_cross_modal_plain_distill": "Plain cross-modal KD",
    "student_xray_cross_modal_plain_distill_balanced": "Plain cross-modal KD + balanced sampler",
    "student_xray_cross_modal_distill": "Full JDCNet",
    "student_xray_cross_modal_distill_balanced": "Full JDCNet + balanced sampler",
}


def _predict_positive_probabilities(config_path: Path, checkpoint_path: Path) -> pd.DataFrame:
    config = load_config(config_path)
    manifest_path = Path(config.manifest_path)
    if not manifest_path.is_absolute():
        manifest_path = SRC_ROOT / manifest_path
    manifest = pd.read_csv(manifest_path)
    val_frame = manifest[manifest["split"] == config.data.val_split].copy().reset_index(drop=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(config.model).to(device)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()
    transform = _build_transform(config.model.input_size, is_train=False)

    probabilities: list[float] = []
    predictions: list[int] = []
    for _, row in val_frame.iterrows():
        image_tensor = transform(_load_rgb_image(row["image_path"])).unsqueeze(0).to(device)
        paired_tensor = None
        if config.model.paired_input or config.distillation.enabled:
            paired_path = row.get(config.data.paired_image_column, row["image_path"])
            paired_tensor = transform(_load_rgb_image(paired_path)).unsqueeze(0).to(device)
        with torch.no_grad():
            if paired_tensor is not None:
                try:
                    logits = model(image_tensor, paired_tensor)
                except TypeError:
                    logits = model(image_tensor)
            else:
                logits = model(image_tensor)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        probabilities.append(float(probs[1]))
        predictions.append(int(probs.argmax()))

    val_frame["positive_probability"] = probabilities
    val_frame["predicted_label"] = predictions
    return val_frame


def _compute_binary_metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = (probabilities >= threshold).astype(int)
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    specificity = float(tn / (tn + fp)) if (tn + fp) else 0.0
    positive_rate = float(predictions.mean())
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "specificity": specificity,
        "positive_prediction_rate": positive_rate,
        "threshold": threshold,
    }


def _run_balanced_controls(
    seeds: list[int],
    config_dir: Path,
    runs_root: Path,
    paired_cross_manifest_path: Path,
    batch_size: int,
    input_size: int,
    epochs: int,
    force: bool,
) -> None:
    specs = []
    for seed in seeds:
        specs.extend(
            [
                (
                    f"student_xray_supervised_paired_balanced_s{seed}",
                    _build_config(
                        experiment_name=f"student_xray_supervised_paired_balanced_s{seed}",
                        manifest_path=paired_cross_manifest_path,
                        output_dir=f"runs/covid_matrix/student_xray_supervised_paired_balanced_s{seed}",
                        seed=seed,
                        model_name="student",
                        train_modalities=["xray"],
                        val_modalities=["xray"],
                        batch_size=batch_size,
                        input_size=input_size,
                        epochs=epochs,
                        distillation_enabled=False,
                        use_weighted_sampler=True,
                    ),
                ),
                (
                    f"student_xray_cross_modal_plain_distill_balanced_s{seed}",
                    _build_config(
                        experiment_name=f"student_xray_cross_modal_plain_distill_balanced_s{seed}",
                        manifest_path=paired_cross_manifest_path,
                        output_dir=f"runs/covid_matrix/student_xray_cross_modal_plain_distill_balanced_s{seed}",
                        seed=seed,
                        model_name="student",
                        train_modalities=["xray"],
                        val_modalities=["xray"],
                        batch_size=batch_size,
                        input_size=input_size,
                        epochs=epochs,
                        distillation_enabled=True,
                        teacher_checkpoint=f"runs/covid_matrix/teacher_ct_all_plain_s{seed}/best.pt",
                        use_dpe=False,
                        use_mhra=False,
                        use_dfpn=False,
                        use_weighted_sampler=True,
                    ),
                ),
                (
                    f"student_xray_cross_modal_distill_balanced_s{seed}",
                    _build_config(
                        experiment_name=f"student_xray_cross_modal_distill_balanced_s{seed}",
                        manifest_path=paired_cross_manifest_path,
                        output_dir=f"runs/covid_matrix/student_xray_cross_modal_distill_balanced_s{seed}",
                        seed=seed,
                        model_name="student",
                        train_modalities=["xray"],
                        val_modalities=["xray"],
                        batch_size=batch_size,
                        input_size=input_size,
                        epochs=epochs,
                        distillation_enabled=True,
                        teacher_checkpoint=f"runs/covid_matrix/teacher_ct_all_s{seed}/best.pt",
                        use_weighted_sampler=True,
                    ),
                ),
            ]
        )

    for run_name, config_payload in specs:
        config_path = config_dir / f"{run_name}.json"
        _write_config(config_path, config_payload)
        _run_training_config(config_path, runs_root / run_name, force=force)


def _build_control_summary(run_frame: pd.DataFrame) -> pd.DataFrame:
    summary = _aggregate_mean_std(run_frame, CONTROL_GROUPS)
    summary["display_name"] = summary["experiment_group"].map(DISPLAY_NAMES)
    summary["protocol"] = summary["experiment_group"].map(
        lambda name: "Balanced sampler" if name.endswith("_balanced") else "Original training"
    )
    summary["family"] = summary["experiment_group"].map(
        {
            "student_xray_supervised_paired": "Student-only",
            "student_xray_supervised_paired_balanced": "Student-only",
            "student_xray_cross_modal_plain_distill": "Plain cross-modal KD",
            "student_xray_cross_modal_plain_distill_balanced": "Plain cross-modal KD",
            "student_xray_cross_modal_distill": "Full JDCNet",
            "student_xray_cross_modal_distill_balanced": "Full JDCNet",
        }
    )
    return summary


def _build_threshold_analysis(config_dir: Path, runs_root: Path, seeds: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    probability_rows: list[dict[str, object]] = []
    threshold_rows: list[dict[str, object]] = []
    thresholds = [round(value, 2) for value in np.linspace(0.1, 0.9, 9)]

    for experiment_group in CONTROL_GROUPS:
        for seed in seeds:
            run_name = f"{experiment_group}_s{seed}"
            config_path = config_dir / f"{run_name}.json"
            checkpoint_path = runs_root / run_name / "best.pt"
            val_frame = _predict_positive_probabilities(config_path, checkpoint_path)
            val_frame["experiment_group"] = experiment_group
            val_frame["display_name"] = DISPLAY_NAMES[experiment_group]
            val_frame["seed"] = seed
            probability_rows.extend(val_frame.to_dict("records"))

            labels = val_frame["label"].to_numpy(dtype=int)
            probabilities = val_frame["positive_probability"].to_numpy(dtype=float)
            for threshold in thresholds:
                metrics = _compute_binary_metrics(labels, probabilities, threshold=threshold)
                threshold_rows.append(
                    {
                        "experiment_group": experiment_group,
                        "display_name": DISPLAY_NAMES[experiment_group],
                        "seed": seed,
                        **metrics,
                    }
                )

    probability_frame = pd.DataFrame(probability_rows)
    threshold_frame = pd.DataFrame(threshold_rows)
    return probability_frame, threshold_frame


def _plot_control_sanity(summary_frame: pd.DataFrame, threshold_frame: pd.DataFrame, output_path: Path) -> None:
    family_order = ["Student-only", "Plain cross-modal KD", "Full JDCNet"]
    protocol_order = ["Original training", "Balanced sampler"]
    colors = {
        ("Student-only", "Original training"): "#355070",
        ("Student-only", "Balanced sampler"): "#6d597a",
        ("Plain cross-modal KD", "Original training"): "#f4a261",
        ("Plain cross-modal KD", "Balanced sampler"): "#e9c46a",
        ("Full JDCNet", "Original training"): "#2a9d8f",
        ("Full JDCNet", "Balanced sampler"): "#8ab17d",
    }

    figure, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)

    summary_index = summary_frame.set_index(["family", "protocol"])
    x_positions = np.arange(len(family_order))
    width = 0.34
    for offset_index, protocol in enumerate(protocol_order):
        balanced_scores = []
        specificity_scores = []
        labels = []
        for family in family_order:
            row = summary_index.loc[(family, protocol)]
            balanced_scores.append(row["balanced_accuracy_mean"])
            specificity_scores.append(row["specificity_mean"])
            labels.append(family)
        offset = (-width / 2) if offset_index == 0 else (width / 2)
        axes[0].bar(
            x_positions + offset,
            balanced_scores,
            width=width,
            label=protocol,
            color=[colors[(family, protocol)] for family in family_order],
        )
        axes[1].bar(
            x_positions + offset,
            specificity_scores,
            width=width,
            label=protocol,
            color=[colors[(family, protocol)] for family in family_order],
        )

    axes[0].set_xticks(x_positions)
    axes[0].set_xticklabels(family_order, rotation=15, ha="right")
    axes[0].set_ylim(0.0, 1.05)
    axes[0].set_title("Balanced accuracy at threshold 0.5")
    axes[0].grid(axis="y", linestyle="--", alpha=0.25)
    axes[0].legend(loc="upper right")

    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels(family_order, rotation=15, ha="right")
    axes[1].set_ylim(0.0, 1.05)
    axes[1].set_title("Specificity at threshold 0.5")
    axes[1].grid(axis="y", linestyle="--", alpha=0.25)
    axes[1].legend(loc="upper right")

    figure.suptitle("Imbalance-sensitive control experiments on the paired cohort", fontsize=13)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)

    threshold_figure, threshold_axis = plt.subplots(figsize=(8.5, 5), constrained_layout=True)
    line_order = [
        "student_xray_supervised_paired",
        "student_xray_supervised_paired_balanced",
        "student_xray_cross_modal_plain_distill",
        "student_xray_cross_modal_plain_distill_balanced",
        "student_xray_cross_modal_distill",
        "student_xray_cross_modal_distill_balanced",
    ]
    for experiment_group in line_order:
        frame = threshold_frame[threshold_frame["experiment_group"] == experiment_group]
        mean_frame = frame.groupby("threshold")[["balanced_accuracy", "positive_prediction_rate"]].mean().reset_index()
        threshold_axis.plot(
            mean_frame["threshold"],
            mean_frame["balanced_accuracy"],
            marker="o",
            linewidth=2,
            label=DISPLAY_NAMES[experiment_group],
        )
    threshold_axis.set_xlabel("Decision threshold on p(COVID)")
    threshold_axis.set_ylabel("Mean balanced accuracy")
    threshold_axis.set_ylim(0.0, 1.05)
    threshold_axis.set_title("Threshold sensitivity across repeated runs")
    threshold_axis.grid(alpha=0.25, linestyle="--")
    threshold_axis.legend(fontsize=8, ncol=2)
    threshold_figure.savefig(output_path.with_name("covid_threshold_sensitivity.png"), dpi=300, bbox_inches="tight")
    plt.close(threshold_figure)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run imbalance-sensitive control experiments for the COVID matrix.")
    parser.add_argument("--dataset-root", default=r"D:\source\covid-chestxray-dataset")
    parser.add_argument("--data-dir", default=str(SRC_ROOT / "data" / "covid_real"))
    parser.add_argument("--config-dir", default=str(SRC_ROOT / "configs" / "generated_covid"))
    parser.add_argument("--runs-root", default=str(SRC_ROOT / "runs" / "covid_matrix"))
    parser.add_argument("--seeds", default="42,43,44,45")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--input-size", type=int, default=128)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    config_dir = Path(args.config_dir)
    runs_root = Path(args.runs_root)
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]

    _prepare_dataset(dataset_root=Path(args.dataset_root), data_dir=data_dir)
    _ensure_same_modality_manifest(data_dir=data_dir)
    paired_cross_manifest_path = data_dir / "covid_paired_xray_target_manifest.csv"

    _run_balanced_controls(
        seeds=seeds,
        config_dir=config_dir,
        runs_root=runs_root,
        paired_cross_manifest_path=paired_cross_manifest_path,
        batch_size=args.batch_size,
        input_size=args.input_size,
        epochs=args.epochs,
        force=args.force,
    )

    run_frame = _collect_run_rows(runs_root)
    summary_frame = _build_control_summary(run_frame)
    probability_frame, threshold_frame = _build_threshold_analysis(config_dir=config_dir, runs_root=runs_root, seeds=seeds)

    SRC_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    summary_path = SRC_RESULTS_DIR / "covid_control_sanity_summary.csv"
    probability_path = SRC_RESULTS_DIR / "covid_control_val_probabilities.csv"
    threshold_path = SRC_RESULTS_DIR / "covid_threshold_sweep.csv"
    paper_summary_path = PAPER_RESULTS_DIR / "covid_control_sanity_summary.csv"
    paper_probability_path = PAPER_RESULTS_DIR / "covid_control_val_probabilities.csv"
    paper_threshold_path = PAPER_RESULTS_DIR / "covid_threshold_sweep.csv"
    figure_path = PAPER_IMAGE_DIR / "covid_control_sanity.png"

    summary_frame.to_csv(summary_path, index=False)
    probability_frame.to_csv(probability_path, index=False)
    threshold_frame.to_csv(threshold_path, index=False)
    summary_frame.to_csv(paper_summary_path, index=False)
    probability_frame.to_csv(paper_probability_path, index=False)
    threshold_frame.to_csv(paper_threshold_path, index=False)
    _plot_control_sanity(summary_frame, threshold_frame, figure_path)

    report = {
        "summary_csv": str(summary_path),
        "probability_csv": str(probability_path),
        "threshold_csv": str(threshold_path),
        "paper_summary_csv": str(paper_summary_path),
        "paper_probability_csv": str(paper_probability_path),
        "paper_threshold_csv": str(paper_threshold_path),
        "paper_figure": str(figure_path),
        "paper_threshold_figure": str(figure_path.with_name("covid_threshold_sensitivity.png")),
    }
    with open(SRC_RESULTS_DIR / "covid_control_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("Wrote imbalance-sensitive control experiment assets.")


if __name__ == "__main__":
    main()
