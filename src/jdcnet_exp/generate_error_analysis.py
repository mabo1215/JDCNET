from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import torch

from .config import load_config
from .data import _build_transform, _load_rgb_image
from .models import build_model


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
PAPER_RESULTS = ROOT / "paper" / "results"
PAPER_TABLES = ROOT / "paper" / "tables" / "generated"

MODEL_SPECS = [
    ("Student-only", "configs/generated_covid/student_xray_supervised_paired_s42.json", "runs/covid_matrix/student_xray_supervised_paired_s42/best.pt"),
    ("Late fusion", "configs/generated_covid/late_fusion_paired_s42.json", "runs/covid_matrix/late_fusion_paired_s42/best.pt"),
    ("Same-modality KD", "configs/generated_covid/student_xray_same_modality_distill_s42.json", "runs/covid_matrix/student_xray_same_modality_distill_s42/best.pt"),
    ("Cross-modality KD", "configs/generated_covid/student_xray_cross_modal_distill_s42.json", "runs/covid_matrix/student_xray_cross_modal_distill_s42/best.pt"),
    ("Cross-modality KD w/o MHRA", "configs/generated_covid/student_xray_cross_modal_distill_nomhra_s42.json", "runs/covid_matrix/student_xray_cross_modal_distill_nomhra_s42/best.pt"),
]


def _latex_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("&", r"\&")
        .replace("%", r"\%")
    )


def _predict_row(model: torch.nn.Module, config, row: pd.Series, device: torch.device) -> tuple[int, float]:
    transform = _build_transform(config.model.input_size, is_train=False)
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
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]
    return int(probabilities.argmax()), float(probabilities[1])


def _write_failure_table(frame: pd.DataFrame) -> None:
    rows = []
    for _, row in frame.iterrows():
        short_image = _latex_escape(Path(row["image_path"]).name)
        truth = "COVID" if int(row["label"]) == 1 else "Non-COVID"
        rows.append(
            f"{_latex_escape(row['patient_id'])} & {short_image} & {truth} & "
            f"{row['Student-only_pred']} & {row['Late fusion_pred']} & {row['Same-modality KD_pred']} & "
            f"{row['Cross-modality KD_pred']} & {row['Cross-modality KD w/o MHRA_pred']} \\\\ \\hline"
        )

    table = "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\caption{Representative seed-42 predictions for the four-image paired validation split. The table is intended for qualitative error analysis only and should not be interpreted as a substitute for the repeated-run summaries in the main text.}",
            r"\label{tab:paired_failure_cases}",
            r"\centering",
            r"\begin{tabular}{|c|l|c|c|c|c|c|c|}",
            r"\hline",
            r"Patient & X-ray File & Ground Truth & Student-only & Late fusion & Same-modality KD & Cross-modality KD & KD w/o MHRA \\ \hline",
            *rows,
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    (PAPER_TABLES / "failure_cases.tex").write_text(table + "\n", encoding="utf-8")


def main() -> None:
    manifest_path = SRC_ROOT / "data" / "covid_real" / "covid_paired_xray_target_manifest.csv"
    manifest = pd.read_csv(manifest_path)
    val_frame = manifest[manifest["split"] == "val"].copy().reset_index(drop=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    for label, config_rel, checkpoint_rel in MODEL_SPECS:
        config = load_config(SRC_ROOT / config_rel)
        model = build_model(config.model).to(device)
        model.load_state_dict(torch.load(SRC_ROOT / checkpoint_rel, map_location=device))
        model.eval()

        predictions: list[str] = []
        positive_scores: list[float] = []
        for _, row in val_frame.iterrows():
            predicted_label, positive_score = _predict_row(model, config, row, device)
            predictions.append("COVID" if predicted_label == 1 else "Non-COVID")
            positive_scores.append(positive_score)

        val_frame[f"{label}_pred"] = predictions
        val_frame[f"{label}_p_covid"] = positive_scores

    output_csv = PAPER_RESULTS / "paired_failure_analysis.csv"
    PAPER_RESULTS.mkdir(parents=True, exist_ok=True)
    val_frame.to_csv(output_csv, index=False)
    _write_failure_table(val_frame)

    report = {
        "failure_analysis_csv": str(output_csv),
        "failure_cases_table": str(PAPER_TABLES / "failure_cases.tex"),
    }
    with open(SRC_ROOT / "results" / "failure_analysis_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"Wrote {output_csv}")


if __name__ == "__main__":
    main()
