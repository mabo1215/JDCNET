from __future__ import annotations

import json
from math import sqrt
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = ROOT / "src" / "results" / "paper_metrics.json"
PAPER_IMAGE_DIR = ROOT / "paper" / "images" / "generated"
PAPER_RESULTS_DIR = ROOT / "paper" / "results"


def _summarize_metrics(payload: dict[str, list[dict[str, object]]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for modality, items in payload.items():
        for item in items:
            runs = item["runs"]
            mean_accuracy = sum(runs) / len(runs)
            variance = sum((value - mean_accuracy) ** 2 for value in runs) / len(runs)
            rows.append(
                {
                    "modality": modality,
                    "model": item["model"],
                    "acc_1": runs[0],
                    "acc_2": runs[1],
                    "acc_3": runs[2],
                    "acc_4": runs[3],
                    "average_accuracy": mean_accuracy,
                    "recall": item["recall"],
                    "variance": variance,
                    "standard_deviation": sqrt(variance),
                }
            )
    return pd.DataFrame(rows)


def _plot_accuracy_recall(summary_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    color_accuracy = "#2a6f97"
    color_recall = "#d98e04"

    for axis, modality, title in zip(
        axes,
        ["xray", "ct"],
        ["Chest X-ray", "CT"],
    ):
        subset = summary_df[summary_df["modality"] == modality].reset_index(drop=True)
        x_positions = list(range(len(subset)))
        axis.bar(
            [value - 0.2 for value in x_positions],
            subset["average_accuracy"],
            width=0.4,
            label="Average accuracy",
            color=color_accuracy,
        )
        axis.bar(
            [value + 0.2 for value in x_positions],
            subset["recall"],
            width=0.4,
            label="Recall",
            color=color_recall,
        )
        axis.set_xticks(x_positions)
        axis.set_xticklabels(subset["model"], rotation=35, ha="right")
        axis.set_ylim(0.84, 1.01)
        axis.set_title(title)
        axis.grid(axis="y", linestyle="--", alpha=0.35)

    axes[0].set_ylabel("Score")
    axes[1].legend(loc="lower left")
    fig.suptitle("Programmatically generated summary of average accuracy and recall")
    fig.savefig(PAPER_IMAGE_DIR / "summary_metrics.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_stability(summary_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    line_color = "#355070"
    point_color = "#6d597a"

    for axis, modality, title in zip(
        axes,
        ["xray", "ct"],
        ["Chest X-ray", "CT"],
    ):
        subset = summary_df[summary_df["modality"] == modality].reset_index(drop=True)
        x_positions = list(range(len(subset)))
        axis.errorbar(
            x_positions,
            subset["average_accuracy"],
            yerr=subset["standard_deviation"],
            fmt="o",
            color=point_color,
            ecolor=line_color,
            elinewidth=1.5,
            capsize=4,
            markersize=6,
        )
        axis.set_xticks(x_positions)
        axis.set_xticklabels(subset["model"], rotation=35, ha="right")
        axis.set_ylim(0.84, 1.01)
        axis.set_title(title)
        axis.set_ylabel("Average accuracy")
        axis.grid(axis="y", linestyle="--", alpha=0.35)

    fig.suptitle("Mean accuracy with standard deviation across four runs")
    fig.savefig(PAPER_IMAGE_DIR / "stability_metrics.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    PAPER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_PATH, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    summary_df = _summarize_metrics(payload)
    summary_df.to_csv(PAPER_RESULTS_DIR / "generated_metrics.csv", index=False)

    _plot_accuracy_recall(summary_df)
    _plot_stability(summary_df)

    print(f"Wrote {PAPER_RESULTS_DIR / 'generated_metrics.csv'}")
    print(f"Wrote {PAPER_IMAGE_DIR / 'summary_metrics.png'}")
    print(f"Wrote {PAPER_IMAGE_DIR / 'stability_metrics.png'}")


if __name__ == "__main__":
    main()
