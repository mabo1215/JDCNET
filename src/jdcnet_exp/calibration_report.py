#!/usr/bin/env python3
"""E6 Calibration report: ECE, reliability diagrams, and Youden-J threshold.

For each of the 11 student/fusion methods across 10 Monte Carlo resamples,
loads best.pt, runs inference on the val split, pools probabilities across
resamples, and computes calibration metrics.

Outputs:
  - paper/figs/generated/calibration_table.tex
  - paper/figs/covid_calibration_reliability.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Allow running as `python calibration_report.py` from src/
_SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SRC))

from jdcnet_exp.config import (
    DataConfig,
    DistillationConfig,
    ExperimentConfig,
    ModelConfig,
    OptimizationConfig,
)
from jdcnet_exp.data import create_dataloaders
from jdcnet_exp.models import build_model

# ---------------------------------------------------------------------------
# Method → model config mapping (mirrors run_covid_resampling.py exactly)
# ---------------------------------------------------------------------------

_METHODS: list[dict] = [
    dict(
        key="student_xray_supervised_resampled",
        label="Student-only",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=True,  # trained with default use_dfpn=True in run_covid_resampling
        paired_input=False,
    ),
    dict(
        key="late_fusion_resampled",
        label="Late fusion",
        manifest="cross",
        model_name="late_fusion",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=True,
    ),
    dict(
        key="student_xray_same_modality_distill_resampled",
        label="Same-modal KD",
        manifest="same",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=True,  # trained with default use_dfpn=True in run_covid_resampling
        paired_input=False,
    ),
    dict(
        key="student_xray_cross_modal_plain_distill_resampled",
        label="Plain cross-modal KD",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
    dict(
        key="student_xray_cross_modal_attention_transfer_resampled",
        label="Attention transfer",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
    dict(
        key="student_xray_cross_modal_feature_hint_resampled",
        label="Feature hint",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
    dict(
        key="student_xray_cross_modal_distill_resampled",
        label="Full JDCNet",
        manifest="cross",
        model_name="student",
        use_dpe=True,
        use_mhra=True,
        use_dfpn=True,
        paired_input=False,
    ),
    dict(
        key="student_xray_modality_hallucination_resampled",
        label="Modality-hallucination KD",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
    dict(
        key="student_xray_crd_resampled",
        label="CRD",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
    dict(
        key="student_xray_dkd_resampled",
        label="DKD",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
    dict(
        key="student_xray_dist_resampled",
        label="DIST",
        manifest="cross",
        model_name="student",
        use_dpe=False,
        use_mhra=False,
        use_dfpn=False,
        paired_input=False,
    ),
]

_N_SPLITS = 10
_INPUT_SIZE = 128
_NUM_CLASSES = 2
_N_BINS = 5  # small number of bins given tiny val sets; pooled ECE uses 10


def _build_config(method: dict, split_idx: int, runs_dir: Path, data_dir: Path) -> ExperimentConfig:
    suffix = f"r{split_idx:02d}"
    split_dir = data_dir / f"split_{split_idx:02d}"

    if method["manifest"] == "cross":
        manifest_path = str(split_dir / "paired_cross_manifest.csv")
    elif method["manifest"] == "same":
        manifest_path = str(split_dir / "paired_same_modality_manifest.csv")
    else:
        raise ValueError(f"Unknown manifest type: {method['manifest']}")

    paired_image_col = "teacher_image_path"
    include_paired = method["paired_input"]

    return ExperimentConfig(
        experiment_name=f"{method['key']}_{suffix}",
        manifest_path=manifest_path,
        output_dir=str(runs_dir / f"{method['key']}_{suffix}"),
        seed=0,
        model=ModelConfig(
            name=method["model_name"],
            num_classes=_NUM_CLASSES,
            input_size=_INPUT_SIZE,
            use_dpe=method["use_dpe"],
            use_mhra=method["use_mhra"],
            use_dfpn=method["use_dfpn"],
            paired_input=include_paired,
        ),
        data=DataConfig(
            train_split="train",
            val_split="val",
            train_modalities=["xray"] if method["manifest"] != "teacher_ct" else ["ct"],
            val_modalities=["xray"] if method["manifest"] != "teacher_ct" else ["ct"],
            batch_size=16,
            num_workers=0,
            paired_image_column=paired_image_col,
        ),
        optimization=OptimizationConfig(epochs=50, learning_rate=3e-4, weight_decay=1e-4),
        distillation=DistillationConfig(enabled=False),
    )


@torch.no_grad()
def _collect_probs(
    model: torch.nn.Module,
    val_loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (probs_pos, labels) arrays from val_loader inference."""
    all_probs: list[float] = []
    all_labels: list[int] = []

    model.eval()
    for batch in val_loader:
        if len(batch) == 3:
            images, teacher_images, labels = batch
        else:
            images, labels = batch
            teacher_images = None

        images = images.to(device)
        if teacher_images is not None:
            teacher_images = teacher_images.to(device)
            logits = model(images, teacher_images)
        else:
            logits = model(images)

        probs = F.softmax(logits, dim=-1)[:, 1].cpu().numpy()
        all_probs.extend(probs.tolist())
        all_labels.extend(labels.numpy().tolist())

    return np.array(all_probs, dtype=float), np.array(all_labels, dtype=int)


def _ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Expected calibration error with equal-width bins."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs)
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (probs >= lo) & (probs < hi)
        if hi == 1.0:
            mask = (probs >= lo) & (probs <= hi)
        if mask.sum() == 0:
            continue
        bin_acc = labels[mask].mean()
        bin_conf = probs[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def _youden_j(probs: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Return (best_threshold, Youden-J index)."""
    thresholds = np.linspace(0.0, 1.0, 101)
    best_j = -1.0
    best_thr = 0.5
    for thr in thresholds:
        preds = (probs >= thr).astype(int)
        tp = ((preds == 1) & (labels == 1)).sum()
        tn = ((preds == 0) & (labels == 0)).sum()
        fp = ((preds == 1) & (labels == 0)).sum()
        fn = ((preds == 0) & (labels == 1)).sum()
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        j = sens + spec - 1.0
        if j > best_j:
            best_j = j
            best_thr = float(thr)
    return best_thr, float(best_j)


def _reliability_diagram_ax(ax: plt.Axes, probs: np.ndarray, labels: np.ndarray, label: str, n_bins: int = 5) -> None:
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    acc_per_bin = []
    count_per_bin = []
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (probs >= lo) & (probs < hi)
        if hi == 1.0:
            mask |= probs == hi
        if mask.sum() == 0:
            acc_per_bin.append(np.nan)
        else:
            acc_per_bin.append(labels[mask].mean())
        count_per_bin.append(mask.sum())

    acc_arr = np.array(acc_per_bin)
    valid = ~np.isnan(acc_arr)
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.5)
    ax.plot(
        bin_centers[valid],
        acc_arr[valid],
        "o-",
        lw=1.2,
        ms=5,
        label=f"{label} (ECE={_ece(probs, labels, n_bins=10):.3f})",
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Mean predicted probability", fontsize=8)
    ax.set_ylabel("Fraction of positives", fontsize=8)
    ax.tick_params(labelsize=7)


def main() -> None:
    runs_dir = _SRC / "runs" / "covid_resampling"
    data_dir = _SRC / "data" / "covid_resampling"
    out_fig_dir = _SRC.parent / "paper" / "figs"
    out_tex_dir = out_fig_dir / "generated"
    out_tex_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    results: list[dict] = []

    # One reliability diagram panel per method
    n_methods = len(_METHODS)
    ncols = 4
    nrows = (n_methods + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 3.2, nrows * 3.0))
    axes_flat = axes.flatten()

    for mi, method in enumerate(_METHODS):
        all_probs: list[float] = []
        all_labels: list[int] = []
        skipped = 0

        for split_idx in range(1, _N_SPLITS + 1):
            suffix = f"r{split_idx:02d}"
            run_dir = runs_dir / f"{method['key']}_{suffix}"
            ckpt_path = run_dir / "best.pt"

            if not ckpt_path.exists():
                skipped += 1
                continue

            try:
                config = _build_config(method, split_idx, runs_dir, data_dir)
                _, val_loader = create_dataloaders(config)
                model = build_model(config.model).to(device)
                state = torch.load(ckpt_path, map_location=device)
                model.load_state_dict(state, strict=True)
                probs, labels = _collect_probs(model, val_loader, device)
                all_probs.extend(probs.tolist())
                all_labels.extend(labels.tolist())
            except Exception as exc:
                print(f"  SKIP {method['key']}_{suffix}: {exc}")
                skipped += 1

        if len(all_probs) < 4:
            print(f"  {method['label']}: insufficient data ({len(all_probs)} samples), skipping")
            results.append(dict(
                label=method["label"],
                n=len(all_probs),
                ece=float("nan"),
                youden_thr=float("nan"),
                youden_j=float("nan"),
                skipped=skipped,
            ))
            axes_flat[mi].text(0.5, 0.5, "N/A", ha="center", va="center", transform=axes_flat[mi].transAxes)
            axes_flat[mi].set_title(method["label"], fontsize=8)
            continue

        p = np.array(all_probs)
        y = np.array(all_labels, dtype=int)
        ece_val = _ece(p, y, n_bins=10)
        thr, j_val = _youden_j(p, y)

        print(f"  {method['label']}: n={len(p)}, ECE={ece_val:.3f}, Youden-J thr={thr:.2f} ({j_val:.3f})")
        results.append(dict(
            label=method["label"],
            n=len(p),
            ece=ece_val,
            youden_thr=thr,
            youden_j=j_val,
            skipped=skipped,
        ))

        _reliability_diagram_ax(axes_flat[mi], p, y, method["label"])
        axes_flat[mi].set_title(method["label"], fontsize=8)
        axes_flat[mi].legend(fontsize=6, loc="upper left")

    # Hide unused subplots
    for i in range(n_methods, len(axes_flat)):
        axes_flat[i].set_visible(False)

    fig.suptitle(
        "Reliability diagrams (pooled over 10 resamples, $n_{\\mathrm{val}}$ varies per split)",
        fontsize=10,
    )
    fig.tight_layout()
    out_png = out_fig_dir / "covid_calibration_reliability.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved reliability diagram: {out_png}")

    # LaTeX table
    _write_latex_table(results, out_tex_dir / "calibration_table.tex")


def _fmt(v: float, fmt: str = ".3f") -> str:
    return f"{v:{fmt}}" if not (v != v) else r"--"  # nan check


def _write_latex_table(results: list[dict], path: Path) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Calibration metrics (E6) for all methods, pooled across 10 Monte Carlo "
        r"resamples. ECE = Expected Calibration Error (lower is better, 10 equal-width bins); "
        r"Youden-J threshold = argmax(sensitivity + specificity $-$ 1) over [0, 1]; "
        r"$n$ = total pooled validation samples across all resamples.}",
        r"\label{tab:calibration}",
        r"\setlength{\tabcolsep}{5pt}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Method & $n$ & ECE $\downarrow$ & Youden-J thr. \\",
        r"\midrule",
    ]
    for r in results:
        row = (
            f"{r['label']} & {r['n']} & {_fmt(r['ece'])} & {_fmt(r['youden_thr'])} \\\\"
        )
        lines.append(row)
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved LaTeX table: {path}")


if __name__ == "__main__":
    main()
