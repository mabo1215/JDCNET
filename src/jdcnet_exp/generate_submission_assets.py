from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC_RESULTS = ROOT / "src" / "results"
SRC_DATA = ROOT / "src" / "data" / "covid_real"
SRC_RUNS = ROOT / "src" / "runs" / "covid_matrix"
PAPER_DIR = ROOT / "paper"
TABLE_DIR = PAPER_DIR / "tables" / "generated"
IMAGE_DIR = PAPER_DIR / "images" / "generated"
RESULT_DIR = PAPER_DIR / "results"


def _ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fmt_mean_std(mean_value: float | None, std_value: float | None, missing: str = "--") -> str:
    if mean_value is None or pd.isna(mean_value):
        return missing
    if std_value is None or pd.isna(std_value):
        return f"${mean_value:.3f}$"
    return f"${mean_value:.3f} \\pm {std_value:.3f}$"


def _fmt_float(value: float | None, digits: int = 3, missing: str = "--") -> str:
    if value is None or pd.isna(value):
        return missing
    return f"{value:.{digits}f}"


def _load_dataset_summary() -> dict[str, object]:
    with open(SRC_RESULTS / "covid_dataset_summary.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_dataset_protocol_table(summary: dict[str, object]) -> None:
    mapping = [
        ("All X-ray", summary["xray_all"]),
        ("All CT", summary["ct_all"]),
        ("Paired X-ray target", summary["paired_xray_target"]),
    ]
    rows = []
    for label, payload in mapping:
        rows.append(
            f"{label} & {payload['rows']} & {payload['patients']} & {payload['positives']} & "
            f"{payload['negatives']} & {payload['train_rows']} & {payload['val_rows']} \\\\ \\hline"
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Real-data cohort construction used in the experiments.}",
            r"\label{tab:dataset_protocol}",
            r"\centering",
            r"\begin{tabular}{|l|c|c|c|c|c|c|}",
            r"\hline",
            r"Manifest & Images & Patients & Positives & Negatives & Train Images & Val Images \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "dataset_protocol.tex", table + "\n")


def _write_main_results_table(summary_frame: pd.DataFrame) -> None:
    display_order = [
        "Teacher-only X-ray (all patients)",
        "Teacher-only CT (all patients)",
        "Student-only X-ray (paired cohort)",
        "Late-fusion X-ray+CT",
        "Same-modality distillation",
        "Plain cross-modal logit KD",
        "Cross-modality distillation",
    ]
    rows = []
    frame = summary_frame.set_index("display_name").loc[display_order].reset_index()
    for _, row in frame.iterrows():
        rows.append(
            " & ".join(
                [
                    row["display_name"],
                    _fmt_mean_std(row["accuracy_mean"], row["accuracy_std"]),
                    _fmt_mean_std(row["macro_f1_mean"], row["macro_f1_std"]),
                    _fmt_mean_std(row["balanced_accuracy_mean"], row["balanced_accuracy_std"]),
                ]
            )
            + r" \\ \hline"
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Repeated-run results on the real-data experiment matrix. Values are reported as mean $\pm$ standard deviation across four seeds. We keep the main-text table focused on accuracy, macro-F1, and balanced accuracy because the paired validation split is too small for threshold-sensitive secondary metrics to be stable. The CT-only teacher result is included only as a reference because its validation split contains only positive cases.}",
            r"\label{tab:real_results}",
            r"\centering",
            r"\begin{tabular}{|l|c|c|c|}",
            r"\hline",
            r"Experiment & Accuracy & Macro-F1 & Balanced Accuracy \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "main_results.tex", table + "\n")


def _write_split_audit_table() -> None:
    manifests = [
        ("All X-ray", SRC_DATA / "covid_xray_all_manifest.csv"),
        ("All CT", SRC_DATA / "covid_ct_all_manifest.csv"),
        ("Paired X-ray target", SRC_DATA / "covid_paired_xray_target_manifest.csv"),
    ]
    rows = []
    audit_rows: list[dict[str, object]] = []

    for label, path in manifests:
        frame = pd.read_csv(path)
        train_patients = set(frame.loc[frame["split"] == "train", "patient_id"].astype(str))
        val_patients = set(frame.loc[frame["split"] == "val", "patient_id"].astype(str))
        overlap = sorted(train_patients & val_patients)
        train_pos = int(((frame["split"] == "train") & (frame["label"] == 1)).sum())
        train_neg = int(((frame["split"] == "train") & (frame["label"] == 0)).sum())
        val_pos = int(((frame["split"] == "val") & (frame["label"] == 1)).sum())
        val_neg = int(((frame["split"] == "val") & (frame["label"] == 0)).sum())
        rows.append(
            f"{label} & {len(train_patients)} & {len(val_patients)} & {len(overlap)} & "
            f"{train_pos}/{train_neg} & {val_pos}/{val_neg} \\\\ \\hline"
        )
        audit_rows.append(
            {
                "manifest": label,
                "train_patients": len(train_patients),
                "val_patients": len(val_patients),
                "patient_overlap": len(overlap),
                "train_positive_images": train_pos,
                "train_negative_images": train_neg,
                "val_positive_images": val_pos,
                "val_negative_images": val_neg,
            }
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Patient-level split audit for the executable manifests. Overlap counts equal zero for all manifests, but the CT-only and paired validation splits remain extremely small and imbalanced.}",
            r"\label{tab:split_audit}",
            r"\centering",
            r"\begin{tabular}{|l|c|c|c|c|c|}",
            r"\hline",
            r"Manifest & Train Patients & Val Patients & Patient Overlap & Train Pos/Neg & Val Pos/Neg \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "split_audit.tex", table + "\n")
    with open(RESULT_DIR / "split_audit.json", "w", encoding="utf-8") as handle:
        json.dump(audit_rows, handle, indent=2)


def _write_module_ablation_table(module_frame: pd.DataFrame) -> None:
    frame = module_frame.copy()
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            " & ".join(
                [
                    row["display_name"],
                    _fmt_mean_std(row["accuracy_mean"], row["accuracy_std"]),
                    _fmt_mean_std(row["macro_f1_mean"], row["macro_f1_std"]),
                    _fmt_float(row["accuracy_delta_vs_baseline"], missing="0.000"),
                    _fmt_float(row["macro_f1_delta_vs_baseline"], missing="0.000"),
                ]
            )
            + r" \\ \hline"
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Module ablation summary for the cross-modality pipeline. Deltas are reported relative to the baseline cross-modality configuration.}",
            r"\label{tab:module_ablation}",
            r"\centering",
            r"\begin{tabular}{|l|c|c|c|c|}",
            r"\hline",
            r"Configuration & Accuracy & Macro-F1 & $\Delta$ Accuracy & $\Delta$ Macro-F1 \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "module_ablation.tex", table + "\n")


def _write_paired_seed_table(run_frame: pd.DataFrame) -> None:
    paired_groups = [
        "student_xray_supervised_paired",
        "late_fusion_paired",
        "student_xray_same_modality_distill",
        "student_xray_cross_modal_plain_distill",
        "student_xray_cross_modal_distill",
    ]
    display_map = {
        "student_xray_supervised_paired": "Student-only",
        "late_fusion_paired": "Late fusion",
        "student_xray_same_modality_distill": "Same-modality KD",
        "student_xray_cross_modal_plain_distill": "Plain cross-modal KD",
        "student_xray_cross_modal_distill": "Cross-modality KD",
    }
    frame = run_frame[(run_frame["is_ablation"] == False) & (run_frame["experiment_group"].isin(paired_groups))].copy()
    frame = frame.sort_values(by=["seed", "experiment_group"])
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            f"{int(row['seed'])} & {display_map[row['experiment_group']]} & "
            f"{_fmt_float(row['accuracy'])} & {_fmt_float(row['macro_f1'])} & "
            f"{_fmt_float(row['balanced_accuracy'])} & {_fmt_float(row['roc_auc'])} \\\\ \\hline"
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Per-seed results for the paired-cohort models. The table makes the instability of the four-image validation split explicit.}",
            r"\label{tab:paired_seed_results}",
            r"\centering",
            r"\begin{tabular}{|c|l|c|c|c|c|}",
            r"\hline",
            r"Seed & Model & Accuracy & Macro-F1 & Balanced Accuracy & ROC-AUC \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "paired_seed_results.tex", table + "\n")


def _build_paired_confusion_summary() -> pd.DataFrame:
    model_map = {
        "student_xray_supervised_paired": "Student-only",
        "late_fusion_paired": "Late fusion",
        "student_xray_same_modality_distill": "Same-modality KD",
        "student_xray_cross_modal_plain_distill": "Plain cross-modal KD",
        "student_xray_cross_modal_distill": "Cross-modality KD",
        "student_xray_cross_modal_distill_nomhra": "Cross-modal KD w/o MHRA",
    }
    rows = []
    for run_prefix, display_name in model_map.items():
        total = [[0, 0], [0, 0]]
        for seed in (42, 43, 44, 45):
            metrics_path = SRC_RUNS / f"{run_prefix}_s{seed}" / "best_metrics.json"
            with open(metrics_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            matrix = payload["confusion_matrix"]
            total = [[total[i][j] + int(matrix[i][j]) for j in range(2)] for i in range(2)]
        tn, fp = total[0]
        fn, tp = total[1]
        rows.append(
            {
                "display_name": display_name,
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "tp": tp,
                "specificity": tn / (tn + fp) if (tn + fp) else 0.0,
                "recall": tp / (tp + fn) if (tp + fn) else 0.0,
                "total_predictions": tn + fp + fn + tp,
            }
        )
    return pd.DataFrame(rows)


def _write_paired_confusion_table(confusion_frame: pd.DataFrame) -> None:
    rows = []
    for _, row in confusion_frame.iterrows():
        rows.append(
            f"{row['display_name']} & {int(row['tn'])} & {int(row['fp'])} & {int(row['fn'])} & {int(row['tp'])} & "
            f"{_fmt_float(row['specificity'])} & {_fmt_float(row['recall'])} \\\\ \\hline"
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Seed-aggregated confusion summaries for the paired-cohort models. Counts are summed over the four repeated runs on the same four validation images, so the table is intended to show qualitative error tendencies rather than to create a larger independent test set.}",
            r"\label{tab:paired_confusion_summary}",
            r"\centering",
            r"\begin{tabular}{|l|c|c|c|c|c|c|}",
            r"\hline",
            r"Model & TN & FP & FN & TP & Specificity & Recall \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "paired_confusion_summary.tex", table + "\n")


def _plot_paired_confusion_summary(confusion_frame: pd.DataFrame) -> None:
    figure, axes = plt.subplots(1, len(confusion_frame), figsize=(14.5, 3.0), constrained_layout=True)
    if len(confusion_frame) == 1:
        axes = [axes]

    max_value = int(confusion_frame[["tn", "fp", "fn", "tp"]].to_numpy().max())
    image = None
    for axis, (_, row) in zip(axes, confusion_frame.iterrows()):
        matrix = [[int(row["tn"]), int(row["fp"])], [int(row["fn"]), int(row["tp"])]]
        image = axis.imshow(matrix, cmap="Blues", vmin=0, vmax=max_value)
        axis.set_title(str(row["display_name"]), fontsize=9)
        axis.set_xticks([0, 1], labels=["Pred Neg", "Pred Pos"])
        axis.set_yticks([0, 1], labels=["True Neg", "True Pos"])
        axis.tick_params(axis="both", labelsize=8)
        for i in range(2):
            for j in range(2):
                axis.text(j, i, str(matrix[i][j]), ha="center", va="center", color="#102a43", fontsize=10, fontweight="bold")

    figure.suptitle(
        "Seed-aggregated paired-cohort confusion matrices (4 validation images x 4 seeds)",
        fontsize=12,
        y=0.98,
    )
    if image is not None:
        colorbar = figure.colorbar(image, ax=axes, shrink=0.88, fraction=0.03, pad=0.02)
        colorbar.ax.tick_params(labelsize=8)
    figure.savefig(IMAGE_DIR / "paired_confusion_summary.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def _plot_paired_seed_instability(run_frame: pd.DataFrame) -> None:
    paired_groups = [
        "student_xray_supervised_paired",
        "late_fusion_paired",
        "student_xray_same_modality_distill",
        "student_xray_cross_modal_plain_distill",
        "student_xray_cross_modal_distill",
    ]
    display_map = {
        "student_xray_supervised_paired": "Student-only",
        "late_fusion_paired": "Late fusion",
        "student_xray_same_modality_distill": "Same-modality KD",
        "student_xray_cross_modal_plain_distill": "Plain cross-modal KD",
        "student_xray_cross_modal_distill": "Cross-modality KD",
    }
    frame = run_frame[(run_frame["is_ablation"] == False) & (run_frame["experiment_group"].isin(paired_groups))].copy()
    frame["display_name"] = frame["experiment_group"].map(display_map)

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    metrics = [("accuracy", "Accuracy"), ("macro_f1", "Macro-F1")]
    color_map = {
        "Student-only": "#355070",
        "Late fusion": "#6d597a",
        "Same-modality KD": "#2a9d8f",
        "Plain cross-modal KD": "#f4a261",
        "Cross-modality KD": "#e76f51",
    }

    for axis, (metric_name, title) in zip(axes, metrics):
        for position, group in enumerate(paired_groups):
            group_frame = frame[frame["experiment_group"] == group].copy()
            x_values = [position + offset for offset in [-0.12, -0.04, 0.04, 0.12][: len(group_frame)]]
            axis.scatter(
                x_values,
                group_frame[metric_name],
                s=55,
                color=color_map[display_map[group]],
                alpha=0.9,
                zorder=3,
            )
            axis.hlines(
                y=group_frame[metric_name].mean(),
                xmin=position - 0.18,
                xmax=position + 0.18,
                color=color_map[display_map[group]],
                linewidth=2,
            )
        axis.set_xticks(range(len(paired_groups)))
        axis.set_xticklabels([display_map[group] for group in paired_groups], rotation=18, ha="right")
        axis.set_ylim(0.0, 1.05)
        axis.set_title(title)
        axis.grid(axis="y", linestyle="--", alpha=0.3)

    figure.suptitle("Per-seed instability of the paired-cohort models")
    figure.savefig(IMAGE_DIR / "covid_paired_seed_instability.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def _draw_box(axis, xy, width, height, text, facecolor, fontsize=10.5):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor=facecolor,
        edgecolor="#243b53",
        linewidth=1.7,
    )
    axis.add_patch(box)
    axis.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#102a43",
        wrap=True,
        family="DejaVu Sans",
    )


def _draw_arrow(axis, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=18,
        linewidth=1.7,
        color="#486581",
        shrinkA=0,
        shrinkB=0,
        joinstyle="miter",
    )
    axis.add_patch(arrow)


def _draw_segment_label(axis, start, end, text, position=0.5, offset=0.12, fontsize=9.8):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return

    base_x = start[0] + position * dx
    base_y = start[1] + position * dy
    normal_x = -dy / length
    normal_y = dx / length
    angle = math.degrees(math.atan2(dy, dx))

    axis.text(
        base_x + offset * normal_x,
        base_y + offset * normal_y,
        text,
        fontsize=fontsize,
        color="#486581",
        ha="center",
        va="center",
        rotation=angle,
        rotation_mode="anchor",
        family="DejaVu Sans",
        bbox={"boxstyle": "round,pad=0.08", "facecolor": "white", "edgecolor": "none", "alpha": 0.92},
    )


def _draw_elbow_arrow(axis, points, label=None, label_segment=0, label_position=0.5, label_offset=0.22):
    if len(points) < 2:
        return

    for start, end in zip(points[:-2], points[1:-1]):
        axis.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color="#486581",
            linewidth=1.7,
            solid_capstyle="round",
        )

    _draw_arrow(axis, points[-2], points[-1])

    if label is not None and 0 <= label_segment < len(points) - 1:
        _draw_segment_label(
            axis,
            points[label_segment],
            points[label_segment + 1],
            label,
            position=label_position,
            offset=label_offset,
        )


def _draw_optional_box(axis, xy, width, height, text, fontsize=10.5):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.03,rounding_size=0.12",
        facecolor="#e6def6",
        edgecolor="#7c6bb0",
        linewidth=1.9,
        linestyle=(0, (4, 2)),
        zorder=2,
    )
    axis.add_patch(box)
    axis.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#4a3580",
        family="DejaVu Sans",
        zorder=3,
    )


def _draw_thin_arrow(axis, start, end, color="#486581", lw=1.4, ls=(0, (4, 2))):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=lw,
        color=color,
        linestyle=ls,
        shrinkA=0,
        shrinkB=0,
        zorder=4,
    )
    axis.add_patch(arrow)


def _draw_thin_elbow(axis, points, color="#486581", lw=1.4, ls=(0, (4, 2))):
    for start, end in zip(points[:-2], points[1:-1]):
        axis.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=color,
            linewidth=lw,
            linestyle=ls,
            solid_capstyle="round",
            zorder=4,
        )
    _draw_thin_arrow(axis, points[-2], points[-1], color=color, lw=lw, ls=ls)


def _plot_executable_architecture() -> None:
    figure, axis = plt.subplots(figsize=(15.0, 7.2))
    figure.patch.set_facecolor("white")
    axis.set_xlim(0, 19.5)
    axis.set_ylim(0, 9.5)
    axis.axis("off")

    C_INPUT = "#dbe7f3"
    C_TEACHER = "#f9d8bd"
    C_STUDENT = "#d9efcf"
    C_LOSS = "#fde68a"

    # ── BACKGROUND ZONES ──────────────────────────────────────────────────
    train_bg = FancyBboxPatch(
        (0.28, 4.95), 16.2, 4.1,
        boxstyle="round,pad=0.05",
        facecolor="#fffcf6", edgecolor="#d4a830",
        linewidth=1.2, linestyle=(0, (6, 3)), alpha=0.85, zorder=0,
    )
    axis.add_patch(train_bg)
    axis.text(
        0.52, 8.82, "Training phase only",
        fontsize=9.0, color="#9a7215", fontstyle="italic", va="top", zorder=1,
    )

    deploy_bg = FancyBboxPatch(
        (0.28, 0.55), 12.7, 4.15,
        boxstyle="round,pad=0.05",
        facecolor="#f5fbf5", edgecolor="#6ab87a",
        linewidth=1.2, linestyle=(0, (6, 3)), alpha=0.85, zorder=0,
    )
    axis.add_patch(deploy_bg)
    axis.text(
        0.52, 4.45, "Deployment path  (X-ray only)",
        fontsize=9.0, color="#3a7d44", fontstyle="italic", va="top", zorder=1,
    )

    # ── TEACHER PATH  (row centre y ≈ 6.55) ───────────────────────────────
    _draw_box(axis, (0.60, 6.0), 1.85, 1.1, "CT\ninput", C_INPUT, fontsize=10.0)
    _draw_box(
        axis, (2.85, 5.65), 2.75, 1.8,
        "Teacher encoder\n4 conv stages\n(32→64→128→256 ch)", C_TEACHER, fontsize=9.4,
    )
    _draw_optional_box(axis, (6.2, 6.0), 1.45, 1.1, "DPE", fontsize=10.5)
    _draw_optional_box(axis, (8.1, 6.0), 1.6, 1.1, "MHRA", fontsize=10.5)
    _draw_box(
        axis, (10.2, 5.65), 2.5, 1.8,
        "Teacher\nfeatures &\nsoft targets", C_TEACHER, fontsize=10.0,
    )

    _draw_arrow(axis, (2.45, 6.55), (2.85, 6.55))
    _draw_arrow(axis, (5.60, 6.55), (6.20, 6.55))
    _draw_arrow(axis, (7.65, 6.55), (8.10, 6.55))
    _draw_arrow(axis, (9.70, 6.55), (10.2, 6.55))

    # ── STUDENT PATH  (row centre y ≈ 2.30) ───────────────────────────────
    _draw_box(axis, (0.60, 1.75), 1.85, 1.1, "X-ray\ninput", C_INPUT, fontsize=10.0)
    _draw_box(
        axis, (2.85, 1.45), 2.75, 1.7,
        "Student encoder\n3 conv stages\n(32→64→128 ch)", C_STUDENT, fontsize=9.4,
    )
    _draw_optional_box(axis, (6.2, 1.75), 1.6, 1.1, "DFPN", fontsize=10.5)
    _draw_box(
        axis, (8.4, 1.45), 2.5, 1.7,
        "Student\nembedding &\nlogits", C_STUDENT, fontsize=10.0,
    )

    _draw_arrow(axis, (2.45, 2.30), (2.85, 2.30))
    _draw_arrow(axis, (5.60, 2.30), (6.20, 2.30))
    _draw_arrow(axis, (7.80, 2.30), (8.40, 2.30))

    # ── LOSS BOXES ────────────────────────────────────────────────────────
    _draw_box(axis, (13.4, 6.3), 2.15, 0.95, "Soft KL loss\n(T = τ)", C_LOSS, fontsize=9.5)
    _draw_box(axis, (13.4, 5.0), 2.15, 0.95, "Attn. transfer\nloss", C_LOSS, fontsize=9.5)
    _draw_box(axis, (13.4, 1.75), 2.15, 0.95, "Hard CE loss", C_LOSS, fontsize=9.5)
    _draw_box(
        axis, (16.5, 3.5), 2.3, 2.2,
        "Total\ntraining loss\nL", C_LOSS, fontsize=10.5,
    )

    # ── DISTILLATION CONNECTIONS ──────────────────────────────────────────
    # Teacher logits → Soft KL  (solid)
    _draw_elbow_arrow(
        axis,
        [(12.70, 6.55), (13.05, 6.55), (13.40, 6.775)],
        label="soft targets",
        label_segment=0, label_position=0.38, label_offset=0.16,
    )

    # Student logits → Soft KL  (dashed, elbow up)
    _draw_thin_elbow(
        axis,
        [(10.90, 2.50), (11.95, 2.50), (11.95, 6.775), (13.40, 6.775)],
        color="#486581", lw=1.45,
    )
    axis.text(
        12.20, 4.90, "student\nlogits",
        fontsize=8.5, color="#486581", ha="center", va="center", zorder=5,
        bbox={"boxstyle": "round,pad=0.12", "facecolor": "white", "edgecolor": "none", "alpha": 0.92},
    )

    # Teacher refined features → AT loss  (solid, elbow down)
    _draw_elbow_arrow(
        axis,
        [(11.45, 5.65), (11.45, 5.475), (13.40, 5.475)],
        label="attn. maps",
        label_segment=1, label_position=0.52, label_offset=0.16,
    )

    # Student deepest feature → AT loss  (dashed, elbow up)
    _draw_thin_elbow(
        axis,
        [(10.90, 2.10), (12.15, 2.10), (12.15, 5.475), (13.40, 5.475)],
        color="#486581", lw=1.45,
    )

    # Student logits → Hard CE  (solid)
    _draw_elbow_arrow(
        axis,
        [(10.90, 2.30), (13.40, 2.225)],
        label="hard labels  y",
        label_segment=0, label_position=0.45, label_offset=0.16,
    )

    # Loss components → Total loss
    _draw_elbow_arrow(axis, [(15.55, 6.775), (15.90, 6.775), (15.90, 5.70), (16.50, 5.70)])
    _draw_elbow_arrow(axis, [(15.55, 5.475), (15.90, 5.475), (15.90, 5.20), (16.50, 5.20)])
    _draw_elbow_arrow(axis, [(15.55, 2.225), (15.90, 2.225), (15.90, 4.50), (16.50, 4.50)])

    # ── TITLE ─────────────────────────────────────────────────────────────
    axis.text(
        9.5, 9.20,
        "JDCNet scaffold evaluated in this study",
        fontsize=16.5, fontweight="semibold", ha="center", color="#102a43",
        family="DejaVu Sans", zorder=5,
    )

    # ── LEGEND NOTE ───────────────────────────────────────────────────────
    axis.text(
        0.52, 0.12,
        "─ ─   Optional module (value empirically tested; DPE on teacher, MHRA on teacher, DFPN on student)",
        fontsize=8.6, color="#4a3580", va="bottom", zorder=5, family="DejaVu Sans",
    )

    figure.savefig(IMAGE_DIR / "jdcnet_executable_architecture.png", dpi=400, bbox_inches="tight", pad_inches=0.06)
    figure.savefig(IMAGE_DIR / "jdcnet_executable_architecture.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(figure)


def _write_implementation_details_table() -> None:
    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Implementation details for the executable scaffold used in this study.}",
            r"\label{tab:implementation_details}",
            r"\centering",
            r"\begin{tabular}{|l|l|}",
            r"\hline",
            r"Item & Setting \\ \hline",
            r"Teacher backbone & 4-stage convolutional encoder (32/64/128/256 channels) \\ \hline",
            r"Student backbone & 3-stage convolutional encoder (32/64/128 channels) \\ \hline",
            r"DPE implementation & $1 \times 1$ convolution + spatial softmax reweighting \\ \hline",
            r"MHRA implementation & batch-first multi-head attention + sigmoid retain gate \\ \hline",
            r"DFPN implementation & 3-scale top-down pyramid with lateral $1 \times 1$ and output $3 \times 3$ convolutions \\ \hline",
            r"Input resolution & $128 \times 128$ \\ \hline",
            r"Optimizer & AdamW \\ \hline",
            r"Learning rate & $3 \times 10^{-4}$ \\ \hline",
            r"Weight decay & $1 \times 10^{-4}$ \\ \hline",
            r"Batch size & 16 \\ \hline",
            r"Epochs & 5 \\ \hline",
            r"Random seeds & 42, 43, 44, 45 \\ \hline",
            r"Distillation objective & hard cross-entropy + soft KL divergence \\ \hline",
            r"Temperature ablation & $\{2, 4, 6\}$ \\ \hline",
            r"Alpha ablation & $\{0.3, 0.6, 0.9\}$ \\ \hline",
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    _write_text(TABLE_DIR / "implementation_details.tex", table + "\n")


def _plot_main_results(summary_frame: pd.DataFrame, run_frame: pd.DataFrame) -> None:
    plot_order = [
        "teacher_xray_all",
        "student_xray_supervised_paired",
        "late_fusion_paired",
        "student_xray_same_modality_distill",
        "student_xray_cross_modal_plain_distill",
        "student_xray_cross_modal_distill",
    ]
    short_names = {
        "teacher_xray_all": "Teacher X-ray",
        "student_xray_supervised_paired": "Student-only",
        "late_fusion_paired": "Late fusion",
        "student_xray_same_modality_distill": "Same-modality KD",
        "student_xray_cross_modal_plain_distill": "Plain cross-modal KD",
        "student_xray_cross_modal_distill": "Cross-modality KD",
    }
    colors = {
        "teacher_xray_all": "#355070",
        "student_xray_supervised_paired": "#2a9d8f",
        "late_fusion_paired": "#6d597a",
        "student_xray_same_modality_distill": "#577590",
        "student_xray_cross_modal_plain_distill": "#f4a261",
        "student_xray_cross_modal_distill": "#e76f51",
    }
    plot_frame = summary_frame[summary_frame["experiment_group"].isin(plot_order)].copy()
    plot_frame = plot_frame.sort_values(
        by="experiment_group",
        key=lambda series: series.map({name: index for index, name in enumerate(plot_order)}),
    )
    seed_frame = run_frame[(run_frame["is_ablation"] == False) & (run_frame["experiment_group"].isin(plot_order))].copy()

    figure, axes = plt.subplots(1, 3, figsize=(17, 5.5), constrained_layout=True)
    metrics = [
        ("accuracy", "Accuracy"),
        ("macro_f1", "Macro-F1"),
        ("balanced_accuracy", "Balanced Accuracy"),
    ]

    for axis, (metric_name, title) in zip(axes, metrics):
        for position, (_, row) in enumerate(plot_frame.iterrows()):
            group = row["experiment_group"]
            mean_value = row[f"{metric_name}_mean"]
            std_value = row[f"{metric_name}_std"] if not pd.isna(row[f"{metric_name}_std"]) else 0.0
            axis.bar(
                position,
                mean_value,
                yerr=std_value,
                color=colors[group],
                alpha=0.85,
                capsize=4,
                width=0.7,
            )
            group_runs = seed_frame[seed_frame["experiment_group"] == group].reset_index(drop=True)
            offsets = [-0.12, -0.04, 0.04, 0.12]
            x_values = [position + offsets[index] for index in range(len(group_runs))]
            axis.scatter(
                x_values,
                group_runs[metric_name],
                color="white",
                edgecolor="black",
                s=42,
                linewidth=0.8,
                zorder=4,
            )
        axis.set_xticks(range(len(plot_frame)))
        axis.set_xticklabels([short_names[name] for name in plot_frame["experiment_group"]], rotation=20, ha="right")
        axis.set_ylim(0.0, 1.05)
        axis.set_title(title)
        axis.grid(axis="y", linestyle="--", alpha=0.25)

    figure.suptitle("Repeated-run performance with per-seed variability", fontsize=14)
    figure.savefig(IMAGE_DIR / "covid_matrix_main.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def _plot_module_ablation(module_frame: pd.DataFrame, run_frame: pd.DataFrame) -> None:
    plot_order = [
        "student_xray_cross_modal_distill",
        "student_xray_cross_modal_distill_nodpe",
        "student_xray_cross_modal_distill_nomhra",
        "student_xray_cross_modal_distill_nodfpn",
    ]
    short_names = {
        "student_xray_cross_modal_distill": "Baseline",
        "student_xray_cross_modal_distill_nodpe": "w/o DPE",
        "student_xray_cross_modal_distill_nomhra": "w/o MHRA",
        "student_xray_cross_modal_distill_nodfpn": "w/o DFPN",
    }
    colors = {
        "student_xray_cross_modal_distill": "#355070",
        "student_xray_cross_modal_distill_nodpe": "#6d597a",
        "student_xray_cross_modal_distill_nomhra": "#e76f51",
        "student_xray_cross_modal_distill_nodfpn": "#2a9d8f",
    }
    plot_frame = module_frame.set_index("experiment_group").loc[plot_order].reset_index()
    seed_frame = run_frame[(run_frame["is_ablation"] == False) & (run_frame["experiment_group"].isin(plot_order))].copy()
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    metrics = [("accuracy", "Accuracy"), ("macro_f1", "Macro-F1")]

    for axis, (metric_name, title) in zip(axes, metrics):
        for position, (_, row) in enumerate(plot_frame.iterrows()):
            group = row["experiment_group"]
            axis.bar(
                position,
                row[f"{metric_name}_mean"],
                yerr=row[f"{metric_name}_std"] if not pd.isna(row[f"{metric_name}_std"]) else 0.0,
                color=colors[group],
                alpha=0.85,
                capsize=4,
                width=0.68,
            )
            group_runs = seed_frame[seed_frame["experiment_group"] == group].reset_index(drop=True)
            offsets = [-0.12, -0.04, 0.04, 0.12]
            x_values = [position + offsets[index] for index in range(len(group_runs))]
            axis.scatter(
                x_values,
                group_runs[metric_name],
                color="white",
                edgecolor="black",
                s=42,
                linewidth=0.8,
                zorder=4,
            )
        axis.set_xticks(range(len(plot_frame)))
        axis.set_xticklabels([short_names[name] for name in plot_frame["experiment_group"]], rotation=18, ha="right")
        axis.set_ylim(0.0, 1.05)
        axis.set_title(title)
        axis.grid(axis="y", linestyle="--", alpha=0.25)

    figure.suptitle("Module ablations with per-seed variability", fontsize=14)
    figure.savefig(IMAGE_DIR / "covid_matrix_module_ablation.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    _ensure_dirs()
    summary = _load_dataset_summary()
    summary_frame = pd.read_csv(SRC_RESULTS / "covid_matrix_summary.csv")
    run_frame = pd.read_csv(SRC_RESULTS / "covid_matrix_per_run.csv")
    module_frame = pd.read_csv(SRC_RESULTS / "covid_matrix_module_ablation.csv")
    confusion_frame = _build_paired_confusion_summary()

    _write_dataset_protocol_table(summary)
    _write_main_results_table(summary_frame)
    _write_split_audit_table()
    _write_module_ablation_table(module_frame)
    _write_paired_seed_table(run_frame)
    _write_paired_confusion_table(confusion_frame)
    _write_implementation_details_table()
    _plot_executable_architecture()
    _plot_main_results(summary_frame, run_frame)
    _plot_module_ablation(module_frame, run_frame)
    _plot_paired_seed_instability(run_frame)
    _plot_paired_confusion_summary(confusion_frame)
    confusion_frame.to_csv(RESULT_DIR / "paired_confusion_summary.csv", index=False)

    report = {
        "dataset_protocol_table": str(TABLE_DIR / "dataset_protocol.tex"),
        "main_results_table": str(TABLE_DIR / "main_results.tex"),
        "split_audit_table": str(TABLE_DIR / "split_audit.tex"),
        "module_ablation_table": str(TABLE_DIR / "module_ablation.tex"),
        "paired_seed_results_table": str(TABLE_DIR / "paired_seed_results.tex"),
        "paired_confusion_summary_table": str(TABLE_DIR / "paired_confusion_summary.tex"),
        "implementation_details_table": str(TABLE_DIR / "implementation_details.tex"),
        "architecture_figure": str(IMAGE_DIR / "jdcnet_executable_architecture.png"),
        "paired_seed_instability_figure": str(IMAGE_DIR / "covid_paired_seed_instability.png"),
        "paired_confusion_summary_figure": str(IMAGE_DIR / "paired_confusion_summary.png"),
    }
    with open(SRC_RESULTS / "submission_assets_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("Generated submission assets for paper/ and appendix.")


if __name__ == "__main__":
    main()
