from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
RESULTS_DIR = ROOT / "src" / "results"
PAPER_IMAGE_DIR = ROOT / "paper" / "images" / "generated"
PAPER_RESULTS_DIR = ROOT / "paper" / "results"


BASE_EXPERIMENTS = [
    "teacher_xray_all",
    "teacher_ct_all",
    "student_xray_supervised_paired",
    "student_xray_same_modality_distill",
    "student_xray_cross_modal_distill",
]

DISPLAY_NAMES = {
    "teacher_xray_all": "Teacher-only X-ray (all patients)",
    "teacher_ct_all": "Teacher-only CT (all patients)",
    "student_xray_supervised_paired": "Student-only X-ray (paired cohort)",
    "student_xray_same_modality_distill": "Same-modality distillation",
    "student_xray_cross_modal_distill": "Cross-modality distillation",
}


def _parse_int_list(raw_value: str) -> list[int]:
    return [int(item.strip()) for item in raw_value.split(",") if item.strip()]


def _write_json(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _write_config(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def _prepare_dataset(dataset_root: Path, data_dir: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "jdcnet_exp.prepare_covid_dataset",
        "--dataset-root",
        str(dataset_root),
        "--output-dir",
        str(data_dir),
    ]
    _run_command(command, workdir=SRC_ROOT)


def _ensure_same_modality_manifest(data_dir: Path) -> Path:
    cross_modal_manifest_path = data_dir / "covid_paired_xray_target_manifest.csv"
    same_modal_manifest_path = data_dir / "covid_paired_xray_same_modality_manifest.csv"
    manifest = pd.read_csv(cross_modal_manifest_path)
    manifest["teacher_image_path"] = manifest["image_path"]
    manifest["teacher_modality"] = manifest["modality"]
    manifest.to_csv(same_modal_manifest_path, index=False)
    return same_modal_manifest_path


def _build_config(
    experiment_name: str,
    manifest_path: Path,
    output_dir: str,
    seed: int,
    model_name: str,
    train_modalities: list[str],
    val_modalities: list[str],
    batch_size: int,
    input_size: int,
    epochs: int,
    distillation_enabled: bool,
    teacher_checkpoint: str = "",
    temperature: float = 4.0,
    alpha: float = 0.6,
) -> dict[str, object]:
    return {
        "experiment_name": experiment_name,
        "manifest_path": str(manifest_path.relative_to(SRC_ROOT)).replace("\\", "/"),
        "output_dir": output_dir,
        "seed": seed,
        "model": {
            "name": model_name,
            "num_classes": 2,
            "input_size": input_size,
        },
        "data": {
            "train_split": "train",
            "val_split": "val",
            "train_modalities": train_modalities,
            "val_modalities": val_modalities,
            "batch_size": batch_size,
            "num_workers": 0,
        },
        "optimization": {
            "epochs": epochs,
            "learning_rate": 0.0003,
            "weight_decay": 0.0001,
        },
        "distillation": {
            "enabled": distillation_enabled,
            "temperature": temperature,
            "alpha": alpha,
            "teacher_checkpoint": teacher_checkpoint,
        },
    }


def _run_training_config(config_path: Path, output_dir: Path, force: bool) -> None:
    metrics_path = output_dir / "best_metrics.json"
    if metrics_path.exists() and not force:
        print(f"Skipping existing run: {output_dir}")
        return
    command = [sys.executable, "-m", "jdcnet_exp.train", "--config", str(config_path)]
    _run_command(command, workdir=SRC_ROOT)


def _load_metrics(run_dir: Path) -> dict[str, object]:
    with open(run_dir / "best_metrics.json", "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    confusion_matrix = payload.get("confusion_matrix", [[0, 0], [0, 0]])
    val_samples = int(sum(sum(int(value) for value in row) for row in confusion_matrix))
    payload["val_samples"] = val_samples
    return payload


def _collect_run_rows(runs_root: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seed_pattern = re.compile(r"_s(?P<seed>\d+)$")
    ablation_pattern = re.compile(
        r"^(?P<group>student_xray_cross_modal_distill)_t(?P<temperature>[0-9.]+)_a(?P<alpha>[0-9.]+)_s(?P<seed>\d+)$"
    )

    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        metrics_path = run_dir / "best_metrics.json"
        if not metrics_path.exists():
            continue

        run_name = run_dir.name
        metrics = _load_metrics(run_dir)
        ablation_match = ablation_pattern.match(run_name)
        if ablation_match:
            experiment_group = ablation_match.group("group")
            row = {
                "run_name": run_name,
                "experiment_group": experiment_group,
                "seed": int(ablation_match.group("seed")),
                "temperature": float(ablation_match.group("temperature")),
                "alpha": float(ablation_match.group("alpha")),
                "is_ablation": True,
            }
        else:
            seed_match = seed_pattern.search(run_name)
            if not seed_match:
                continue
            experiment_group = run_name[: seed_match.start()]
            row = {
                "run_name": run_name,
                "experiment_group": experiment_group,
                "seed": int(seed_match.group("seed")),
                "temperature": None,
                "alpha": None,
                "is_ablation": False,
            }

        for key, value in metrics.items():
            if isinstance(value, list):
                continue
            row[key] = value
        row["display_name"] = DISPLAY_NAMES.get(experiment_group, experiment_group)
        rows.append(row)

    if not rows:
        raise FileNotFoundError(f"No completed runs found under {runs_root}")
    return pd.DataFrame(rows)


def _aggregate_main_results(run_frame: pd.DataFrame) -> pd.DataFrame:
    base_frame = run_frame[(run_frame["is_ablation"] == False) & (run_frame["experiment_group"].isin(BASE_EXPERIMENTS))].copy()
    metric_columns = [
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "precision",
        "recall",
        "specificity",
        "roc_auc",
        "val_samples",
    ]
    aggregated = (
        base_frame.groupby(["experiment_group", "display_name"])[metric_columns]
        .agg(["mean", "std"])
        .reset_index()
    )
    aggregated.columns = [
        "_".join(column).strip("_") if isinstance(column, tuple) else column for column in aggregated.columns
    ]
    aggregated = aggregated.sort_values(
        by="experiment_group",
        key=lambda series: series.map({name: index for index, name in enumerate(BASE_EXPERIMENTS)}),
    )
    return aggregated


def _prepare_paper_main_table(summary_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in summary_frame.iterrows():
        rows.append(
            {
                "experiment": row["display_name"],
                "accuracy_mean": row["accuracy_mean"],
                "accuracy_std": row["accuracy_std"],
                "macro_f1_mean": row["macro_f1_mean"],
                "macro_f1_std": row["macro_f1_std"],
                "balanced_accuracy_mean": row["balanced_accuracy_mean"],
                "balanced_accuracy_std": row["balanced_accuracy_std"],
                "roc_auc_mean": row["roc_auc_mean"],
                "roc_auc_std": row["roc_auc_std"],
                "recall_mean": row["recall_mean"],
                "recall_std": row["recall_std"],
                "specificity_mean": row["specificity_mean"],
                "specificity_std": row["specificity_std"],
                "val_samples_mean": row["val_samples_mean"],
            }
        )
    return pd.DataFrame(rows)


def _aggregate_ablation_results(run_frame: pd.DataFrame) -> pd.DataFrame:
    ablation_frame = run_frame[run_frame["is_ablation"] == True].copy()
    if ablation_frame.empty:
        return pd.DataFrame()
    return ablation_frame.sort_values(by=["temperature", "alpha"]).reset_index(drop=True)


def _plot_main_results(summary_frame: pd.DataFrame, output_path: Path) -> None:
    plot_frame = summary_frame[
        summary_frame["experiment_group"].isin(
            [
                "teacher_xray_all",
                "student_xray_supervised_paired",
                "student_xray_same_modality_distill",
                "student_xray_cross_modal_distill",
            ]
        )
    ].copy()
    plot_frame["short_name"] = plot_frame["experiment_group"].map(
        {
            "teacher_xray_all": "Teacher X-ray",
            "student_xray_supervised_paired": "Student only",
            "student_xray_same_modality_distill": "Same-modality KD",
            "student_xray_cross_modal_distill": "Cross-modality KD",
        }
    )

    figure, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    metrics = [
        ("accuracy", "Accuracy", "#355070"),
        ("macro_f1", "Macro-F1", "#6d597a"),
        ("balanced_accuracy", "Balanced Accuracy", "#2a6f97"),
    ]
    x_positions = list(range(len(plot_frame)))

    for axis, (metric_name, title, color) in zip(axes, metrics):
        axis.bar(
            x_positions,
            plot_frame[f"{metric_name}_mean"],
            yerr=plot_frame[f"{metric_name}_std"].fillna(0.0),
            color=color,
            alpha=0.9,
            capsize=4,
        )
        axis.set_xticks(x_positions)
        axis.set_xticklabels(plot_frame["short_name"], rotation=25, ha="right")
        axis.set_ylim(0.0, 1.05)
        axis.set_title(title)
        axis.grid(axis="y", linestyle="--", alpha=0.3)

    figure.suptitle("Repeated-run performance on the paired X-ray target cohort")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def _plot_ablation(ablation_frame: pd.DataFrame, output_path: Path) -> None:
    if ablation_frame.empty:
        return

    pivot_frame = ablation_frame.pivot(index="temperature", columns="alpha", values="macro_f1")
    figure, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    image = axis.imshow(pivot_frame.to_numpy(), cmap="YlGnBu", aspect="auto")
    axis.set_xticks(range(len(pivot_frame.columns)))
    axis.set_xticklabels([f"{value:g}" for value in pivot_frame.columns])
    axis.set_yticks(range(len(pivot_frame.index)))
    axis.set_yticklabels([f"{value:g}" for value in pivot_frame.index])
    axis.set_xlabel("alpha")
    axis.set_ylabel("temperature")
    axis.set_title("Cross-modality distillation ablation (Macro-F1)")

    for row_index, temperature in enumerate(pivot_frame.index):
        for col_index, alpha in enumerate(pivot_frame.columns):
            value = pivot_frame.loc[temperature, alpha]
            axis.text(col_index, row_index, f"{value:.3f}", ha="center", va="center", color="black")

    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def _write_paper_assets(run_frame: pd.DataFrame, summary_frame: pd.DataFrame, ablation_frame: pd.DataFrame) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    per_run_path = RESULTS_DIR / "covid_matrix_per_run.csv"
    summary_path = RESULTS_DIR / "covid_matrix_summary.csv"
    ablation_path = RESULTS_DIR / "covid_matrix_ablation.csv"
    paper_main_table_path = PAPER_RESULTS_DIR / "covid_matrix_main_results.csv"
    paper_ablation_path = PAPER_RESULTS_DIR / "covid_matrix_ablation_results.csv"
    main_figure_path = PAPER_IMAGE_DIR / "covid_matrix_main.png"
    ablation_figure_path = PAPER_IMAGE_DIR / "covid_matrix_ablation.png"

    run_frame.to_csv(per_run_path, index=False)
    summary_frame.to_csv(summary_path, index=False)
    if not ablation_frame.empty:
        ablation_frame.to_csv(ablation_path, index=False)
    _prepare_paper_main_table(summary_frame).to_csv(paper_main_table_path, index=False)
    if not ablation_frame.empty:
        ablation_frame.to_csv(paper_ablation_path, index=False)

    _plot_main_results(summary_frame, main_figure_path)
    _plot_ablation(ablation_frame, ablation_figure_path)

    report_payload = {
        "per_run_csv": str(per_run_path),
        "summary_csv": str(summary_path),
        "ablation_csv": str(ablation_path) if not ablation_frame.empty else None,
        "paper_main_results_csv": str(paper_main_table_path),
        "paper_ablation_results_csv": str(paper_ablation_path) if not ablation_frame.empty else None,
        "paper_main_figure": str(main_figure_path),
        "paper_ablation_figure": str(ablation_figure_path) if not ablation_frame.empty else None,
    }
    _write_json(report_payload, RESULTS_DIR / "covid_matrix_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the COVID chest X-ray experiment matrix.")
    parser.add_argument(
        "--dataset-root",
        default=r"D:\source\covid-chestxray-dataset",
        help="Root of the covid-chestxray-dataset repository.",
    )
    parser.add_argument("--data-dir", default=str(SRC_ROOT / "data" / "covid_real"))
    parser.add_argument("--config-dir", default=str(SRC_ROOT / "configs" / "generated_covid"))
    parser.add_argument("--runs-root", default=str(SRC_ROOT / "runs" / "covid_matrix"))
    parser.add_argument("--seeds", default="42,43,44,45")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--input-size", type=int, default=128)
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    data_dir = Path(args.data_dir)
    config_dir = Path(args.config_dir)
    runs_root = Path(args.runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)

    _prepare_dataset(dataset_root=dataset_root, data_dir=data_dir)
    same_modal_manifest_path = _ensure_same_modality_manifest(data_dir=data_dir)

    xray_manifest_path = data_dir / "covid_xray_all_manifest.csv"
    ct_manifest_path = data_dir / "covid_ct_all_manifest.csv"
    paired_cross_manifest_path = data_dir / "covid_paired_xray_target_manifest.csv"

    seeds = _parse_int_list(args.seeds)
    for seed in seeds:
        experiment_specs = [
            (
                f"teacher_xray_all_s{seed}",
                _build_config(
                    experiment_name=f"teacher_xray_all_s{seed}",
                    manifest_path=xray_manifest_path,
                    output_dir=f"runs/covid_matrix/teacher_xray_all_s{seed}",
                    seed=seed,
                    model_name="teacher",
                    train_modalities=["xray"],
                    val_modalities=["xray"],
                    batch_size=args.batch_size,
                    input_size=args.input_size,
                    epochs=args.epochs,
                    distillation_enabled=False,
                ),
            ),
            (
                f"teacher_ct_all_s{seed}",
                _build_config(
                    experiment_name=f"teacher_ct_all_s{seed}",
                    manifest_path=ct_manifest_path,
                    output_dir=f"runs/covid_matrix/teacher_ct_all_s{seed}",
                    seed=seed,
                    model_name="teacher",
                    train_modalities=["ct"],
                    val_modalities=["ct"],
                    batch_size=args.batch_size,
                    input_size=args.input_size,
                    epochs=args.epochs,
                    distillation_enabled=False,
                ),
            ),
        ]

        for run_name, config_payload in experiment_specs:
            config_path = config_dir / f"{run_name}.json"
            _write_config(config_path, config_payload)
            _run_training_config(config_path, runs_root / run_name, force=args.force)

        student_specs = [
            (
                f"student_xray_supervised_paired_s{seed}",
                _build_config(
                    experiment_name=f"student_xray_supervised_paired_s{seed}",
                    manifest_path=paired_cross_manifest_path,
                    output_dir=f"runs/covid_matrix/student_xray_supervised_paired_s{seed}",
                    seed=seed,
                    model_name="student",
                    train_modalities=["xray"],
                    val_modalities=["xray"],
                    batch_size=args.batch_size,
                    input_size=args.input_size,
                    epochs=args.epochs,
                    distillation_enabled=False,
                ),
            ),
            (
                f"student_xray_same_modality_distill_s{seed}",
                _build_config(
                    experiment_name=f"student_xray_same_modality_distill_s{seed}",
                    manifest_path=same_modal_manifest_path,
                    output_dir=f"runs/covid_matrix/student_xray_same_modality_distill_s{seed}",
                    seed=seed,
                    model_name="student",
                    train_modalities=["xray"],
                    val_modalities=["xray"],
                    batch_size=args.batch_size,
                    input_size=args.input_size,
                    epochs=args.epochs,
                    distillation_enabled=True,
                    teacher_checkpoint=f"runs/covid_matrix/teacher_xray_all_s{seed}/best.pt",
                    temperature=4.0,
                    alpha=0.6,
                ),
            ),
            (
                f"student_xray_cross_modal_distill_s{seed}",
                _build_config(
                    experiment_name=f"student_xray_cross_modal_distill_s{seed}",
                    manifest_path=paired_cross_manifest_path,
                    output_dir=f"runs/covid_matrix/student_xray_cross_modal_distill_s{seed}",
                    seed=seed,
                    model_name="student",
                    train_modalities=["xray"],
                    val_modalities=["xray"],
                    batch_size=args.batch_size,
                    input_size=args.input_size,
                    epochs=args.epochs,
                    distillation_enabled=True,
                    teacher_checkpoint=f"runs/covid_matrix/teacher_ct_all_s{seed}/best.pt",
                    temperature=4.0,
                    alpha=0.6,
                ),
            ),
        ]

        for run_name, config_payload in student_specs:
            config_path = config_dir / f"{run_name}.json"
            _write_config(config_path, config_payload)
            _run_training_config(config_path, runs_root / run_name, force=args.force)

    if not args.skip_ablation:
        for temperature in [2.0, 4.0, 6.0]:
            for alpha in [0.3, 0.6, 0.9]:
                run_name = f"student_xray_cross_modal_distill_t{temperature:g}_a{alpha:g}_s42"
                config_payload = _build_config(
                    experiment_name=run_name,
                    manifest_path=paired_cross_manifest_path,
                    output_dir=f"runs/covid_matrix/{run_name}",
                    seed=42,
                    model_name="student",
                    train_modalities=["xray"],
                    val_modalities=["xray"],
                    batch_size=args.batch_size,
                    input_size=args.input_size,
                    epochs=args.epochs,
                    distillation_enabled=True,
                    teacher_checkpoint="runs/covid_matrix/teacher_ct_all_s42/best.pt",
                    temperature=temperature,
                    alpha=alpha,
                )
                config_path = config_dir / f"{run_name}.json"
                _write_config(config_path, config_payload)
                _run_training_config(config_path, runs_root / run_name, force=args.force)

    run_frame = _collect_run_rows(runs_root)
    summary_frame = _aggregate_main_results(run_frame)
    ablation_frame = _aggregate_ablation_results(run_frame)
    _write_paper_assets(run_frame, summary_frame, ablation_frame)

    print("Wrote updated experiment CSVs and figures into paper/.")


if __name__ == "__main__":
    main()
