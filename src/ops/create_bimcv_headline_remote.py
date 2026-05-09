from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path("/data/JDCNET/src")
DATA_DIR = ROOT / "data" / "bimcv"
CONFIG_DIR = ROOT / "configs" / "bimcv_headline"
TASK_DIR = ROOT / "ops" / "job_pool" / "tasks"
LOG_DIR = Path("/data/logs")
RUN_DIR = ROOT / "runs" / "bimcv_headline"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_task(path: Path, config_path: Path, log_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rel_config = config_path.relative_to(ROOT)
    body = f"""#!/usr/bin/env bash
set -euo pipefail
cd /data/JDCNET/src
export PYTHONPATH=/data/JDCNET/src
export CUDA_VISIBLE_DEVICES="${{CUDA_VISIBLE_DEVICES:-0}}"
export PYTHONUNBUFFERED=1
mkdir -p /data/logs
python3 -u -m jdcnet_exp.train --config {rel_config.as_posix()} 2>&1 | tee {log_path.as_posix()}
"""
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def base_config(
    *,
    experiment_name: str,
    manifest_path: str,
    output_dir: str,
    model_name: str,
    input_size: int,
    use_dpe: bool = True,
    use_mhra: bool = True,
    use_dfpn: bool = True,
    paired_input: bool = False,
    train_modalities: list[str],
    val_modalities: list[str],
    use_weighted_sampler: bool,
    epochs: int,
    distillation: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "experiment_name": experiment_name,
        "manifest_path": manifest_path,
        "output_dir": output_dir,
        "seed": 42,
        "model": {
            "name": model_name,
            "num_classes": 2,
            "input_size": input_size,
            "use_dpe": use_dpe,
            "use_mhra": use_mhra,
            "use_dfpn": use_dfpn,
            "paired_input": paired_input,
        },
        "data": {
            "train_split": "train",
            "val_split": "val",
            "train_modalities": train_modalities,
            "val_modalities": val_modalities,
            "batch_size": 16,
            "num_workers": 0,
            "paired_image_column": "teacher_image_path",
            "use_weighted_sampler": use_weighted_sampler,
        },
        "optimization": {
            "epochs": epochs,
            "learning_rate": 0.0003,
            "weight_decay": 0.0001,
        },
        "distillation": distillation
        or {
            "enabled": False,
            "temperature": 4.0,
            "alpha": 0.6,
            "teacher_checkpoint": "",
        },
    }


def materialize_manifests() -> dict[str, Path]:
    merged_path = DATA_DIR / "bimcv_merged_paired_manifest.csv"
    if not merged_path.exists():
        raise FileNotFoundError(f"Missing merged BIMCV manifest: {merged_path}")

    merged = pd.read_csv(merged_path)
    required = {"image_path", "teacher_image_path", "label", "modality", "teacher_modality", "split", "patient_id"}
    missing = required - set(merged.columns)
    if missing:
        raise ValueError(f"Merged manifest is missing columns: {sorted(missing)}")

    teacher_ct = merged[["teacher_image_path", "label", "teacher_modality", "split", "patient_id"]].copy()
    teacher_ct = teacher_ct.rename(
        columns={
            "teacher_image_path": "image_path",
            "teacher_modality": "modality",
        }
    )
    teacher_ct = teacher_ct.drop_duplicates(subset=["image_path", "split"]).reset_index(drop=True)
    teacher_ct_path = DATA_DIR / "bimcv_teacher_ct_manifest.csv"
    teacher_ct.to_csv(teacher_ct_path, index=False)

    same_modality = merged.copy()
    same_modality["teacher_image_path"] = same_modality["image_path"]
    same_modality["teacher_modality"] = same_modality["modality"]
    same_modality_path = DATA_DIR / "bimcv_same_modality_manifest.csv"
    same_modality.to_csv(same_modality_path, index=False)

    return {
        "merged": merged_path,
        "teacher_ct": teacher_ct_path,
        "same_modality": same_modality_path,
    }


def materialize_configs(manifests: dict[str, Path], epochs: int) -> dict[str, Path]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    configs: dict[str, dict[str, object]] = {
        "bimcv_xray_supervised_s42": base_config(
            experiment_name="bimcv_xray_supervised_s42",
            manifest_path="data/bimcv/bimcv_merged_paired_manifest.csv",
            output_dir="runs/bimcv_headline/bimcv_xray_supervised_s42",
            model_name="student",
            input_size=224,
            train_modalities=["xray"],
            val_modalities=["xray"],
            use_weighted_sampler=True,
            epochs=epochs,
        ),
        "bimcv_teacher_ct_s42": base_config(
            experiment_name="bimcv_teacher_ct_s42",
            manifest_path="data/bimcv/bimcv_teacher_ct_manifest.csv",
            output_dir="runs/bimcv_headline/bimcv_teacher_ct_s42",
            model_name="teacher",
            input_size=224,
            train_modalities=["ct"],
            val_modalities=["ct"],
            use_weighted_sampler=True,
            epochs=epochs,
        ),
        "bimcv_xray_cross_modal_kd_s42": base_config(
            experiment_name="bimcv_xray_cross_modal_kd_s42",
            manifest_path="data/bimcv/bimcv_merged_paired_manifest.csv",
            output_dir="runs/bimcv_headline/bimcv_xray_cross_modal_kd_s42",
            model_name="student",
            input_size=224,
            train_modalities=["xray"],
            val_modalities=["xray"],
            use_weighted_sampler=True,
            epochs=epochs,
            distillation={
                "enabled": True,
                "temperature": 4.0,
                "alpha": 0.6,
                "teacher_checkpoint": "runs/bimcv_headline/bimcv_teacher_ct_s42/best.pt",
            },
        ),
    }

    config_paths: dict[str, Path] = {}
    for name, payload in configs.items():
        path = CONFIG_DIR / f"{name}.json"
        write_json(path, payload)
        config_paths[name] = path
    return config_paths


def materialize_tasks(config_paths: dict[str, Path]) -> dict[str, Path]:
    task_paths: dict[str, Path] = {}
    for name, config_path in config_paths.items():
        task_path = TASK_DIR / f"task_{name}.sh"
        log_path = LOG_DIR / f"{name}.log"
        write_task(task_path, config_path=config_path, log_path=log_path)
        task_paths[name] = task_path
    return task_paths


def enqueue(task_paths: dict[str, Path]) -> None:
    order = [
        "bimcv_xray_supervised_s42",
        "bimcv_teacher_ct_s42",
        "bimcv_xray_cross_modal_kd_s42",
    ]
    for name in order:
        subprocess.run(
            [str(ROOT / "ops" / "job_pool" / "job_pool_enqueue.sh"), str(task_paths[name])],
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and enqueue BIMCV headline experiments on the 3090 host.")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--enqueue", action="store_true")
    args = parser.parse_args()

    manifests = materialize_manifests()
    config_paths = materialize_configs(manifests, epochs=args.epochs)
    task_paths = materialize_tasks(config_paths)

    print("BIMCV_HEADLINE_PREPARED")
    for label, path in manifests.items():
        print(f"MANIFEST {label}: {path}")
    for label, path in config_paths.items():
        print(f"CONFIG {label}: {path}")
    for label, path in task_paths.items():
        print(f"TASK {label}: {path}")

    if args.enqueue:
        enqueue(task_paths)
        print("BIMCV_HEADLINE_ENQUEUED")


if __name__ == "__main__":
    main()
