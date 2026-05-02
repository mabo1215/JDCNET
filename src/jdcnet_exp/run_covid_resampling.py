from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .run_covid_matrix import (
    ROOT,
    SRC_ROOT,
    _build_config,
    _prepare_dataset,
    _run_training_config,
    _write_config,
)


PAPER_IMAGE_DIR = ROOT / "paper" / "images" / "generated"
PAPER_RESULTS_DIR = ROOT / "paper" / "results"
SRC_RESULTS_DIR = ROOT / "src" / "results"

EXPERIMENT_GROUPS = [
    "student_xray_supervised_resampled",
    "late_fusion_resampled",
    "student_xray_same_modality_distill_resampled",
    "student_xray_cross_modal_plain_distill_resampled",
    "student_xray_cross_modal_attention_transfer_resampled",
    "student_xray_cross_modal_feature_hint_resampled",
    "student_xray_cross_modal_distill_resampled",
    "student_xray_modality_hallucination_resampled",
    "student_xray_crd_resampled",
    "student_xray_dkd_resampled",
    "student_xray_dist_resampled",
]

DISPLAY_NAMES = {
    "student_xray_supervised_resampled": "Student-only X-ray",
    "late_fusion_resampled": "Late-fusion X-ray+CT",
    "student_xray_same_modality_distill_resampled": "Same-modality distillation",
    "student_xray_cross_modal_plain_distill_resampled": "Plain cross-modal logit KD",
    "student_xray_cross_modal_attention_transfer_resampled": "Cross-modal attention transfer",
    "student_xray_cross_modal_feature_hint_resampled": "Cross-modal feature hint",
    "student_xray_cross_modal_distill_resampled": "Full JDCNet",
    "student_xray_modality_hallucination_resampled": "Modality hallucination KD",
    "student_xray_crd_resampled": "CRD (Tian 2020)",
    "student_xray_dkd_resampled": "DKD (Zhao 2022)",
    "student_xray_dist_resampled": "DIST (Yang 2022)",
}

TIER_NAMES = {
    "student_xray_supervised_resampled": "Feasibility controls",
    "late_fusion_resampled": "Feasibility controls",
    "student_xray_same_modality_distill_resampled": "Feasibility controls",
    "student_xray_cross_modal_plain_distill_resampled": "Feasibility controls",
    "student_xray_cross_modal_attention_transfer_resampled": "Mechanism controls",
    "student_xray_cross_modal_feature_hint_resampled": "Mechanism controls",
    "student_xray_cross_modal_distill_resampled": "Proposed-module test",
    "student_xray_modality_hallucination_resampled": "Modern KD baselines",
    "student_xray_crd_resampled": "Modern KD baselines",
    "student_xray_dkd_resampled": "Modern KD baselines",
    "student_xray_dist_resampled": "Modern KD baselines",
}

TIER_COLORS = {
    "Feasibility controls": "#355070",
    "Mechanism controls": "#f4a261",
    "Proposed-module test": "#b56576",
    "Modern KD baselines": "#6a994e",
}

SUMMARY_METRICS = [
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "precision",
    "recall",
    "specificity",
    "mcc",
    "pr_auc",
    "brier",
    "roc_auc",
]


def _write_json(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _patient_level_labels(manifest: pd.DataFrame) -> pd.DataFrame:
    patient_frame = (
        manifest.groupby("patient_id")["label"]
        .max()
        .reset_index()
        .rename(columns={"label": "patient_label"})
    )
    patient_frame["patient_id"] = patient_frame["patient_id"].astype(str)
    return patient_frame


def _sample_validation_patients(
    patient_frame: pd.DataFrame,
    split_index: int,
    val_positive_patients: int,
    val_negative_patients: int,
) -> set[str]:
    rng = np.random.default_rng(1000 + split_index)
    positive_patients = patient_frame.loc[patient_frame["patient_label"] == 1, "patient_id"].tolist()
    negative_patients = patient_frame.loc[patient_frame["patient_label"] == 0, "patient_id"].tolist()
    if len(positive_patients) < 2 or len(negative_patients) < 2:
        raise ValueError("Resampling requires at least two positive and two negative patients.")

    positive_count = min(val_positive_patients, len(positive_patients) - 1)
    negative_count = min(val_negative_patients, len(negative_patients) - 1)
    if positive_count < 1 or negative_count < 1:
        raise ValueError("Resampling must leave at least one train patient per class.")

    val_positive = rng.choice(positive_patients, size=positive_count, replace=False).tolist()
    val_negative = rng.choice(negative_patients, size=negative_count, replace=False).tolist()
    return {str(patient_id) for patient_id in [*val_positive, *val_negative]}


def _assign_split(manifest: pd.DataFrame, val_patients: set[str]) -> pd.DataFrame:
    assigned = manifest.copy()
    assigned["patient_id"] = assigned["patient_id"].astype(str)
    assigned["split"] = assigned["patient_id"].map(lambda patient_id: "val" if patient_id in val_patients else "train")
    return assigned


def _build_same_modality_manifest(cross_manifest: pd.DataFrame) -> pd.DataFrame:
    same_manifest = cross_manifest.copy()
    same_manifest["teacher_image_path"] = same_manifest["image_path"]
    same_manifest["teacher_modality"] = same_manifest["modality"]
    return same_manifest


def _build_teacher_manifest(
    cross_manifest: pd.DataFrame,
    image_column: str,
    modality_column: str,
) -> pd.DataFrame:
    teacher_manifest = cross_manifest[[image_column, "label", modality_column, "split", "patient_id"]].copy()
    teacher_manifest = teacher_manifest.rename(
        columns={
            image_column: "image_path",
            modality_column: "modality",
        }
    )
    teacher_manifest = teacher_manifest.drop_duplicates(subset=["image_path", "split"]).reset_index(drop=True)
    return teacher_manifest


def _summarize_split(cross_manifest: pd.DataFrame, split_index: int) -> dict[str, object]:
    train_frame = cross_manifest[cross_manifest["split"] == "train"]
    val_frame = cross_manifest[cross_manifest["split"] == "val"]
    return {
        "split_index": split_index,
        "train_patients": int(train_frame["patient_id"].nunique()),
        "val_patients": int(val_frame["patient_id"].nunique()),
        "train_images": int(len(train_frame)),
        "val_images": int(len(val_frame)),
        "train_positive_images": int((train_frame["label"] == 1).sum()),
        "train_negative_images": int((train_frame["label"] == 0).sum()),
        "val_positive_images": int((val_frame["label"] == 1).sum()),
        "val_negative_images": int((val_frame["label"] == 0).sum()),
    }


def _materialize_resampled_manifests(
    base_manifest_path: Path,
    output_dir: Path,
    num_resamples: int,
    val_positive_patients: int,
    val_negative_patients: int,
) -> list[dict[str, object]]:
    base_manifest = pd.read_csv(base_manifest_path)
    patient_frame = _patient_level_labels(base_manifest)
    split_specs: list[dict[str, object]] = []

    output_dir.mkdir(parents=True, exist_ok=True)
    for split_index in range(1, num_resamples + 1):
        val_patients = _sample_validation_patients(
            patient_frame=patient_frame,
            split_index=split_index,
            val_positive_patients=val_positive_patients,
            val_negative_patients=val_negative_patients,
        )
        cross_manifest = _assign_split(base_manifest, val_patients)
        same_manifest = _build_same_modality_manifest(cross_manifest)
        teacher_xray_manifest = _build_teacher_manifest(cross_manifest, image_column="image_path", modality_column="modality")
        teacher_ct_manifest = _build_teacher_manifest(
            cross_manifest,
            image_column="teacher_image_path",
            modality_column="teacher_modality",
        )

        split_dir = output_dir / f"split_{split_index:02d}"
        split_dir.mkdir(parents=True, exist_ok=True)
        cross_manifest_path = split_dir / "paired_cross_manifest.csv"
        same_manifest_path = split_dir / "paired_same_modality_manifest.csv"
        teacher_xray_manifest_path = split_dir / "teacher_xray_manifest.csv"
        teacher_ct_manifest_path = split_dir / "teacher_ct_manifest.csv"
        cross_manifest.to_csv(cross_manifest_path, index=False)
        same_manifest.to_csv(same_manifest_path, index=False)
        teacher_xray_manifest.to_csv(teacher_xray_manifest_path, index=False)
        teacher_ct_manifest.to_csv(teacher_ct_manifest_path, index=False)

        split_specs.append(
            {
                "split_index": split_index,
                "cross_manifest_path": cross_manifest_path,
                "same_manifest_path": same_manifest_path,
                "teacher_xray_manifest_path": teacher_xray_manifest_path,
                "teacher_ct_manifest_path": teacher_ct_manifest_path,
                **_summarize_split(cross_manifest, split_index),
            }
        )

    return split_specs


def _run_resampled_split(
    split_spec: dict[str, object],
    config_dir: Path,
    runs_root: Path,
    batch_size: int,
    input_size: int,
    epochs: int,
    force: bool,
) -> None:
    split_index = int(split_spec["split_index"])
    suffix = f"r{split_index:02d}"
    cross_manifest_path = Path(split_spec["cross_manifest_path"])
    same_manifest_path = Path(split_spec["same_manifest_path"])
    teacher_xray_manifest_path = Path(split_spec["teacher_xray_manifest_path"])
    teacher_ct_manifest_path = Path(split_spec["teacher_ct_manifest_path"])

    experiment_specs = [
        (
            f"teacher_xray_paired_{suffix}",
            _build_config(
                experiment_name=f"teacher_xray_paired_{suffix}",
                manifest_path=teacher_xray_manifest_path,
                output_dir=f"runs/covid_resampling/teacher_xray_paired_{suffix}",
                seed=42,
                model_name="teacher",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=False,
            ),
        ),
        (
            f"teacher_ct_paired_plain_{suffix}",
            _build_config(
                experiment_name=f"teacher_ct_paired_plain_{suffix}",
                manifest_path=teacher_ct_manifest_path,
                output_dir=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}",
                seed=42,
                model_name="teacher",
                train_modalities=["ct"],
                val_modalities=["ct"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=False,
                use_dpe=False,
                use_mhra=False,
            ),
        ),
        (
            f"teacher_ct_paired_full_{suffix}",
            _build_config(
                experiment_name=f"teacher_ct_paired_full_{suffix}",
                manifest_path=teacher_ct_manifest_path,
                output_dir=f"runs/covid_resampling/teacher_ct_paired_full_{suffix}",
                seed=42,
                model_name="teacher",
                train_modalities=["ct"],
                val_modalities=["ct"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=False,
            ),
        ),
        (
            f"student_xray_supervised_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_supervised_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_supervised_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=False,
            ),
        ),
        (
            f"late_fusion_resampled_{suffix}",
            _build_config(
                experiment_name=f"late_fusion_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/late_fusion_resampled_{suffix}",
                seed=42,
                model_name="late_fusion",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=False,
                paired_input=True,
            ),
        ),
        (
            f"student_xray_same_modality_distill_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_same_modality_distill_resampled_{suffix}",
                manifest_path=same_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_same_modality_distill_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_xray_paired_{suffix}/best.pt",
            ),
        ),
        (
            f"student_xray_cross_modal_plain_distill_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_cross_modal_plain_distill_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_cross_modal_plain_distill_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
            ),
        ),
        (
            f"student_xray_cross_modal_attention_transfer_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_cross_modal_attention_transfer_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_cross_modal_attention_transfer_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                attention_transfer_weight=0.2,
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
            ),
        ),
        (
            f"student_xray_cross_modal_feature_hint_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_cross_modal_feature_hint_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_cross_modal_feature_hint_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                feature_hint_weight=0.2,
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
            ),
        ),
        (
            f"student_xray_cross_modal_distill_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_cross_modal_distill_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_cross_modal_distill_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_full_{suffix}/best.pt",
            ),
        ),
        (
            f"student_xray_modality_hallucination_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_modality_hallucination_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_modality_hallucination_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                alpha=0.0,
                modality_hallucination_weight=1.0,
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
                use_weighted_sampler=True,
            ),
        ),
        (
            f"student_xray_crd_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_crd_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_crd_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                alpha=0.3,
                crd_weight=0.5,
                crd_temperature=0.07,
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
                use_weighted_sampler=True,
            ),
        ),
        (
            f"student_xray_dkd_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_dkd_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_dkd_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                alpha=0.0,
                dkd_weight=1.0,
                dkd_alpha=1.0,
                dkd_beta=8.0,
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
                use_weighted_sampler=True,
            ),
        ),
        (
            f"student_xray_dist_resampled_{suffix}",
            _build_config(
                experiment_name=f"student_xray_dist_resampled_{suffix}",
                manifest_path=cross_manifest_path,
                output_dir=f"runs/covid_resampling/student_xray_dist_resampled_{suffix}",
                seed=42,
                model_name="student",
                train_modalities=["xray"],
                val_modalities=["xray"],
                batch_size=batch_size,
                input_size=input_size,
                epochs=epochs,
                distillation_enabled=True,
                teacher_checkpoint=f"runs/covid_resampling/teacher_ct_paired_plain_{suffix}/best.pt",
                alpha=0.0,
                dist_weight=1.0,
                dist_beta=1.0,
                dist_gamma=1.0,
                use_dpe=False,
                use_mhra=False,
                use_dfpn=False,
                use_weighted_sampler=True,
            ),
        ),
    ]

    for run_name, config_payload in experiment_specs:
        config_path = config_dir / f"{run_name}.json"
        _write_config(config_path, config_payload)
        _run_training_config(config_path, runs_root / run_name, force=force)


def _collect_resampling_rows(runs_root: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    pattern = re.compile(r"^(?P<group>.+)_r(?P<split>\d+)$")
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        metrics_path = run_dir / "best_metrics.json"
        if not metrics_path.exists():
            continue
        match = pattern.match(run_dir.name)
        if match is None:
            continue
        experiment_group = match.group("group")
        if experiment_group not in EXPERIMENT_GROUPS:
            continue
        with open(metrics_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        row = {
            "run_name": run_dir.name,
            "experiment_group": experiment_group,
            "display_name": DISPLAY_NAMES[experiment_group],
            "tier": TIER_NAMES[experiment_group],
            "split_index": int(match.group("split")),
        }
        for key, value in payload.items():
            if isinstance(value, list):
                continue
            row[key] = value
        rows.append(row)

    if not rows:
        raise FileNotFoundError(f"No resampling runs found under {runs_root}")
    return pd.DataFrame(rows)


def _summarize_resampling(run_frame: pd.DataFrame) -> pd.DataFrame:
    summary_rows: list[dict[str, object]] = []
    for experiment_group in EXPERIMENT_GROUPS:
        group_frame = run_frame[run_frame["experiment_group"] == experiment_group].copy()
        summary_row = {
            "experiment_group": experiment_group,
            "display_name": DISPLAY_NAMES[experiment_group],
            "tier": TIER_NAMES[experiment_group],
            "num_resamples": int(len(group_frame)),
        }
        for metric_name in SUMMARY_METRICS:
            metric_series = pd.to_numeric(group_frame.get(metric_name), errors="coerce").dropna()
            if metric_series.empty:
                summary_row[f"{metric_name}_mean"] = None
                summary_row[f"{metric_name}_std"] = None
                summary_row[f"{metric_name}_q025"] = None
                summary_row[f"{metric_name}_q975"] = None
                continue
            summary_row[f"{metric_name}_mean"] = float(metric_series.mean())
            summary_row[f"{metric_name}_std"] = float(metric_series.std(ddof=1)) if len(metric_series) > 1 else 0.0
            summary_row[f"{metric_name}_q025"] = float(metric_series.quantile(0.025))
            summary_row[f"{metric_name}_q975"] = float(metric_series.quantile(0.975))
        summary_rows.append(summary_row)
    return pd.DataFrame(summary_rows)


def _plot_resampling_summary(run_frame: pd.DataFrame, summary_frame: pd.DataFrame, output_path: Path) -> None:
    plot_frame = summary_frame.set_index("experiment_group").loc[EXPERIMENT_GROUPS].reset_index()
    metrics = [
        ("accuracy", "Accuracy"),
        ("macro_f1", "Macro-F1"),
        ("balanced_accuracy", "Balanced Accuracy"),
    ]

    figure, axes = plt.subplots(1, len(metrics), figsize=(18, 5.2), constrained_layout=True)
    x_positions = list(range(len(plot_frame)))

    for axis, (metric_name, title) in zip(axes, metrics):
        for position, (_, row) in enumerate(plot_frame.iterrows()):
            color = TIER_COLORS[row["tier"]]
            axis.bar(
                position,
                row[f"{metric_name}_mean"],
                yerr=row[f"{metric_name}_std"] if pd.notna(row[f"{metric_name}_std"]) else 0.0,
                color=color,
                alpha=0.88,
                capsize=4,
                width=0.72,
            )
            split_frame = run_frame[run_frame["experiment_group"] == row["experiment_group"]].sort_values("split_index")
            offsets = np.linspace(-0.18, 0.18, len(split_frame)) if len(split_frame) > 1 else np.array([0.0])
            axis.scatter(
                position + offsets,
                split_frame[metric_name],
                color="white",
                edgecolor="#102a43",
                linewidth=0.8,
                s=34,
                zorder=4,
            )
        axis.set_xticks(x_positions)
        axis.set_xticklabels(plot_frame["display_name"], rotation=20, ha="right")
        axis.set_ylim(0.0, 1.05)
        axis.set_title(title)
        axis.grid(axis="y", linestyle="--", alpha=0.25)
        # Vertical separators between tier groups
        for xv in [3.5, 5.5, 6.5]:
            if xv < len(plot_frame) - 0.5:
                axis.axvline(xv, color="#9fb3c8", linestyle=":", linewidth=1.2)

    figure.suptitle("Repeated patient-level Monte Carlo resampling on the paired cohort", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeated patient-level resampling experiments for the paired COVID cohort.")
    parser.add_argument("--dataset-root", default=r"D:\source\covid-chestxray-dataset")
    parser.add_argument("--data-dir", default=str(SRC_ROOT / "data" / "covid_real"))
    parser.add_argument("--resampling-dir", default=str(SRC_ROOT / "data" / "covid_resampling"))
    parser.add_argument("--config-dir", default=str(SRC_ROOT / "configs" / "generated_covid_resampling"))
    parser.add_argument("--runs-root", default=str(SRC_ROOT / "runs" / "covid_resampling"))
    parser.add_argument("--num-resamples", type=int, default=8)
    parser.add_argument("--val-positive-patients", type=int, default=4)
    parser.add_argument("--val-negative-patients", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--input-size", type=int, default=128)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-dataset-prep", action="store_true",
                        help="Skip prepare_covid_dataset if manifests already exist at --data-dir.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    resampling_dir = Path(args.resampling_dir)
    config_dir = Path(args.config_dir)
    runs_root = Path(args.runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)

    base_manifest_check = data_dir / "covid_paired_xray_target_manifest.csv"
    if args.skip_dataset_prep and base_manifest_check.exists():
        print(f"[skip] dataset prep — manifest found at {base_manifest_check}")
    else:
        _prepare_dataset(dataset_root=Path(args.dataset_root), data_dir=data_dir)
    base_manifest_path = base_manifest_check
    split_specs = _materialize_resampled_manifests(
        base_manifest_path=base_manifest_path,
        output_dir=resampling_dir,
        num_resamples=args.num_resamples,
        val_positive_patients=args.val_positive_patients,
        val_negative_patients=args.val_negative_patients,
    )

    for split_spec in split_specs:
        _run_resampled_split(
            split_spec=split_spec,
            config_dir=config_dir,
            runs_root=runs_root,
            batch_size=args.batch_size,
            input_size=args.input_size,
            epochs=args.epochs,
            force=args.force,
        )

    run_frame = _collect_resampling_rows(runs_root)
    summary_frame = _summarize_resampling(run_frame)
    split_frame = pd.DataFrame(split_specs)

    SRC_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    per_run_path = SRC_RESULTS_DIR / "covid_resampling_per_run.csv"
    summary_path = SRC_RESULTS_DIR / "covid_resampling_summary.csv"
    split_path = SRC_RESULTS_DIR / "covid_resampling_split_stats.csv"
    paper_per_run_path = PAPER_RESULTS_DIR / "covid_resampling_per_run.csv"
    paper_summary_path = PAPER_RESULTS_DIR / "covid_resampling_summary.csv"
    paper_split_path = PAPER_RESULTS_DIR / "covid_resampling_split_stats.csv"
    figure_path = PAPER_IMAGE_DIR / "covid_resampling_main.png"

    run_frame.to_csv(per_run_path, index=False)
    summary_frame.to_csv(summary_path, index=False)
    split_frame.to_csv(split_path, index=False)
    run_frame.to_csv(paper_per_run_path, index=False)
    summary_frame.to_csv(paper_summary_path, index=False)
    split_frame.to_csv(paper_split_path, index=False)
    _plot_resampling_summary(run_frame, summary_frame, figure_path)

    report = {
        "per_run_csv": str(per_run_path),
        "summary_csv": str(summary_path),
        "split_stats_csv": str(split_path),
        "paper_per_run_csv": str(paper_per_run_path),
        "paper_summary_csv": str(paper_summary_path),
        "paper_split_stats_csv": str(paper_split_path),
        "paper_figure": str(figure_path),
        "num_resamples": args.num_resamples,
        "val_positive_patients": args.val_positive_patients,
        "val_negative_patients": args.val_negative_patients,
    }
    _write_json(report, SRC_RESULTS_DIR / "covid_resampling_report.json")
    print("Wrote patient-level resampling assets.")


if __name__ == "__main__":
    main()
