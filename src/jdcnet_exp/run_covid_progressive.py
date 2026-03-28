from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import torch

from .config import ModelConfig
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

PROGRESSIVE_GROUPS = [
    "student_xray_cross_modal_plain_distill",
    "student_xray_cross_modal_progressive_dpe",
    "student_xray_cross_modal_progressive_dpe_dfpn",
    "student_xray_cross_modal_distill_nodfpn",
    "student_xray_cross_modal_distill",
]

DISPLAY_NAMES = {
    "student_xray_cross_modal_plain_distill": "Plain logit KD",
    "student_xray_cross_modal_progressive_dpe": "+ DPE",
    "student_xray_cross_modal_progressive_dpe_dfpn": "+ DPE + DFPN",
    "student_xray_cross_modal_distill_nodfpn": "+ DPE + MHRA",
    "student_xray_cross_modal_distill": "+ DPE + MHRA + DFPN",
}


def _count_parameters(config: ModelConfig) -> int:
    model = build_model(config)
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def _run_progressive_experiments(
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
                    f"student_xray_cross_modal_progressive_dpe_s{seed}",
                    _build_config(
                        experiment_name=f"student_xray_cross_modal_progressive_dpe_s{seed}",
                        manifest_path=paired_cross_manifest_path,
                        output_dir=f"runs/covid_matrix/student_xray_cross_modal_progressive_dpe_s{seed}",
                        seed=seed,
                        model_name="student",
                        train_modalities=["xray"],
                        val_modalities=["xray"],
                        batch_size=batch_size,
                        input_size=input_size,
                        epochs=epochs,
                        distillation_enabled=True,
                        teacher_checkpoint=f"runs/covid_matrix/teacher_ct_all_nomhra_s{seed}/best.pt",
                        use_dpe=True,
                        use_mhra=False,
                        use_dfpn=False,
                    ),
                ),
                (
                    f"student_xray_cross_modal_progressive_dpe_dfpn_s{seed}",
                    _build_config(
                        experiment_name=f"student_xray_cross_modal_progressive_dpe_dfpn_s{seed}",
                        manifest_path=paired_cross_manifest_path,
                        output_dir=f"runs/covid_matrix/student_xray_cross_modal_progressive_dpe_dfpn_s{seed}",
                        seed=seed,
                        model_name="student",
                        train_modalities=["xray"],
                        val_modalities=["xray"],
                        batch_size=batch_size,
                        input_size=input_size,
                        epochs=epochs,
                        distillation_enabled=True,
                        teacher_checkpoint=f"runs/covid_matrix/teacher_ct_all_nomhra_s{seed}/best.pt",
                        use_dpe=True,
                        use_mhra=False,
                        use_dfpn=True,
                    ),
                ),
            ]
        )

    for run_name, config_payload in specs:
        config_path = config_dir / f"{run_name}.json"
        _write_config(config_path, config_payload)
        _run_training_config(config_path, runs_root / run_name, force=force)


def _build_progressive_summary(run_frame: pd.DataFrame) -> pd.DataFrame:
    summary = _aggregate_mean_std(run_frame, PROGRESSIVE_GROUPS)
    summary["display_name"] = summary["experiment_group"].map(DISPLAY_NAMES)

    parameter_rows = []
    for experiment_group in PROGRESSIVE_GROUPS:
        if experiment_group == "student_xray_cross_modal_plain_distill":
            teacher_config = ModelConfig(name="teacher", num_classes=2, input_size=128, use_dpe=False, use_mhra=False)
            student_config = ModelConfig(name="student", num_classes=2, input_size=128, use_dfpn=False)
        elif experiment_group == "student_xray_cross_modal_progressive_dpe":
            teacher_config = ModelConfig(name="teacher", num_classes=2, input_size=128, use_dpe=True, use_mhra=False)
            student_config = ModelConfig(name="student", num_classes=2, input_size=128, use_dfpn=False)
        elif experiment_group == "student_xray_cross_modal_progressive_dpe_dfpn":
            teacher_config = ModelConfig(name="teacher", num_classes=2, input_size=128, use_dpe=True, use_mhra=False)
            student_config = ModelConfig(name="student", num_classes=2, input_size=128, use_dfpn=True)
        elif experiment_group == "student_xray_cross_modal_distill_nodfpn":
            teacher_config = ModelConfig(name="teacher", num_classes=2, input_size=128, use_dpe=True, use_mhra=True)
            student_config = ModelConfig(name="student", num_classes=2, input_size=128, use_dfpn=False)
        else:
            teacher_config = ModelConfig(name="teacher", num_classes=2, input_size=128, use_dpe=True, use_mhra=True)
            student_config = ModelConfig(name="student", num_classes=2, input_size=128, use_dfpn=True)

        parameter_rows.append(
            {
                "experiment_group": experiment_group,
                "teacher_params": _count_parameters(teacher_config),
                "student_params": _count_parameters(student_config),
            }
        )

    parameter_frame = pd.DataFrame(parameter_rows)
    summary = summary.merge(parameter_frame, on="experiment_group", how="left")
    summary["total_params"] = summary["teacher_params"] + summary["student_params"]
    summary["total_params_m"] = summary["total_params"] / 1_000_000.0
    return summary


def _plot_progressive(summary_frame: pd.DataFrame, output_path: Path) -> None:
    plot_frame = summary_frame.set_index("experiment_group").loc[PROGRESSIVE_GROUPS].reset_index()
    x_positions = list(range(len(plot_frame)))

    figure, axes = plt.subplots(1, 2, figsize=(13, 4.8), constrained_layout=True)
    axes[0].bar(x_positions, plot_frame["accuracy_mean"], color="#355070", alpha=0.88)
    axes[0].errorbar(
        x_positions,
        plot_frame["accuracy_mean"],
        yerr=plot_frame["accuracy_std"].fillna(0.0),
        fmt="none",
        ecolor="black",
        capsize=4,
    )
    axes[0].set_xticks(x_positions)
    axes[0].set_xticklabels(plot_frame["display_name"], rotation=18, ha="right")
    axes[0].set_ylim(0.0, 1.05)
    axes[0].set_title("Accuracy across progressive complexity")
    axes[0].grid(axis="y", linestyle="--", alpha=0.25)

    axes[1].bar(x_positions, plot_frame["macro_f1_mean"], color="#b56576", alpha=0.88)
    axes[1].errorbar(
        x_positions,
        plot_frame["macro_f1_mean"],
        yerr=plot_frame["macro_f1_std"].fillna(0.0),
        fmt="none",
        ecolor="black",
        capsize=4,
    )
    param_axis = axes[1].twinx()
    param_axis.plot(
        x_positions,
        plot_frame["total_params_m"],
        color="#2a9d8f",
        marker="o",
        linewidth=2,
    )
    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels(plot_frame["display_name"], rotation=18, ha="right")
    axes[1].set_ylim(0.0, 1.05)
    axes[1].set_title("Macro-F1 and total trainable parameters")
    axes[1].grid(axis="y", linestyle="--", alpha=0.25)
    param_axis.set_ylabel("Total parameters (M)")

    figure.suptitle("Progressive module-complexity experiment", fontsize=13)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run progressive module-complexity experiments.")
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

    _run_progressive_experiments(
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
    summary_frame = _build_progressive_summary(run_frame)

    SRC_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    summary_path = SRC_RESULTS_DIR / "covid_progressive_complexity.csv"
    paper_summary_path = PAPER_RESULTS_DIR / "covid_progressive_complexity.csv"
    figure_path = PAPER_IMAGE_DIR / "covid_progressive_complexity.png"
    summary_frame.to_csv(summary_path, index=False)
    summary_frame.to_csv(paper_summary_path, index=False)
    _plot_progressive(summary_frame, figure_path)

    report = {
        "summary_csv": str(summary_path),
        "paper_summary_csv": str(paper_summary_path),
        "paper_figure": str(figure_path),
    }
    with open(SRC_RESULTS_DIR / "covid_progressive_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("Wrote progressive module-complexity assets.")


if __name__ == "__main__":
    main()
