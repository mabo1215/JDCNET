from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelConfig:
    name: str
    num_classes: int
    input_size: int
    use_dpe: bool = True
    use_mhra: bool = True
    use_dfpn: bool = True
    paired_input: bool = False


@dataclass
class DataConfig:
    train_split: str
    val_split: str
    train_modalities: list[str]
    val_modalities: list[str]
    batch_size: int
    num_workers: int
    paired_image_column: str = "teacher_image_path"
    use_weighted_sampler: bool = False


@dataclass
class OptimizationConfig:
    epochs: int
    learning_rate: float
    weight_decay: float


@dataclass
class DistillationConfig:
    enabled: bool
    temperature: float
    alpha: float
    teacher_checkpoint: str


@dataclass
class ExperimentConfig:
    experiment_name: str
    manifest_path: str
    output_dir: str
    seed: int
    model: ModelConfig
    data: DataConfig
    optimization: OptimizationConfig
    distillation: DistillationConfig


def load_config(config_path: str | Path) -> ExperimentConfig:
    with open(config_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return ExperimentConfig(
        experiment_name=payload["experiment_name"],
        manifest_path=payload["manifest_path"],
        output_dir=payload["output_dir"],
        seed=payload["seed"],
        model=ModelConfig(**payload["model"]),
        data=DataConfig(**payload["data"]),
        optimization=OptimizationConfig(**payload["optimization"]),
        distillation=DistillationConfig(**payload["distillation"]),
    )
