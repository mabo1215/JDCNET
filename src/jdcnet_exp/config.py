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
    backbone: str = "custom"  # "custom" | "resnet18" | "biomedclip"


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
    grad_accum_steps: int = 1
    amp: bool = False
    channels_last: bool = False
    torch_compile: bool = False


@dataclass
class DistillationConfig:
    enabled: bool
    temperature: float = 4.0
    alpha: float = 0.5
    teacher_checkpoint: str = ""
    feature_hint_weight: float = 0.0
    attention_transfer_weight: float = 0.0
    feature_hint_dim: int = 128
    # Modern KD baselines (2016--2022). Each weight defaults to 0; a non-zero
    # weight enables the corresponding loss term as an additive contribution
    # alongside the standard hard+soft distillation objective.
    modality_hallucination_weight: float = 0.0
    crd_weight: float = 0.0
    crd_temperature: float = 0.07
    dkd_weight: float = 0.0
    dkd_alpha: float = 1.0
    dkd_beta: float = 8.0
    dist_weight: float = 0.0
    dist_beta: float = 1.0
    dist_gamma: float = 1.0
    # Tier-B-lite: multi-target distillation (prototype + lung-mask).
    prototype_weight: float = 0.0
    prototype_ema: float = 0.95
    prototype_temperature: float = 0.1
    lung_mask_weight: float = 0.0
    lung_mask_model: str = "torchxrayvision_pspnet"
    lung_mask_input_size: int = 224
    # GAP-KD/JDCNet-v2: confidence-gated and projection-compatible transfer.
    confidence_gate_enabled: bool = False
    confidence_gate_threshold: float = 0.0
    confidence_gate_floor: float = 0.0
    confidence_gate_power: float = 1.0
    confidence_gate_requires_correct: bool = True
    projected_attention_weight: float = 0.0


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
