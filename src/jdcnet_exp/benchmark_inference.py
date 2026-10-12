"""Deployment-cost benchmark for the deployed X-ray classifiers.

Measures parameter count, multiply-accumulate operations (MACs), single-image
latency and peak GPU memory for:

* the ResNet-18 X-ray classifier, which is the deployed graph of the supervised
  baseline, of every JDCNet configuration and of the logit-KD comparators
  (training-time supervision does not change the inference graph);
* the module-augmented lightweight student of the historical pilot.

Weights are randomly initialised: latency and memory depend only on the graph.
MACs are counted for convolution and linear layers with forward hooks.

Usage:
    python -m jdcnet_exp.benchmark_inference
"""
from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torchvision import models as tvm

from .models import StudentCNN

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "records" / "derived" / "inference_benchmark.json"

INPUT_SIZE = 224
WARMUP = 50
TIMED = 1000


def resnet18_classifier() -> nn.Module:
    model = tvm.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    return model


def count_macs(model: nn.Module, input_size: int) -> int:
    total = 0

    def conv_hook(module: nn.Conv2d, _inputs, output: torch.Tensor) -> None:
        nonlocal total
        kernel = module.kernel_size[0] * module.kernel_size[1]
        total += int(output.numel() * (module.in_channels // module.groups) * kernel)

    def linear_hook(module: nn.Linear, _inputs, output: torch.Tensor) -> None:
        nonlocal total
        total += int(output.numel() * module.in_features)

    handles = []
    for layer in model.modules():
        if isinstance(layer, nn.Conv2d):
            handles.append(layer.register_forward_hook(conv_hook))
        elif isinstance(layer, nn.Linear):
            handles.append(layer.register_forward_hook(linear_hook))
    with torch.no_grad():
        model(torch.zeros(1, 3, input_size, input_size))
    for handle in handles:
        handle.remove()
    return total


def time_forward(model: nn.Module, device: torch.device) -> dict[str, float]:
    model = model.to(device).eval()
    x = torch.rand(1, 3, INPUT_SIZE, INPUT_SIZE, device=device)
    timings = []
    with torch.no_grad():
        for _ in range(WARMUP):
            model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
        for _ in range(TIMED):
            start = time.perf_counter()
            model(x)
            if device.type == "cuda":
                torch.cuda.synchronize()
            timings.append((time.perf_counter() - start) * 1000.0)
    arr = np.asarray(timings)
    result = {
        "median_ms": float(np.median(arr)),
        "iqr_ms": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
    }
    if device.type == "cuda":
        result["peak_memory_mb"] = float(torch.cuda.max_memory_allocated() / 2**20)
    return result


def main() -> None:
    torch.manual_seed(0)
    torch.set_num_threads(1)
    candidates = {
        "resnet18_xray_classifier": resnet18_classifier,
        "module_augmented_student": lambda: StudentCNN(num_classes=2, use_dfpn=True),
    }
    report: dict[str, object] = {
        "input": f"1x3x{INPUT_SIZE}x{INPUT_SIZE} FP32, batch size 1, model forward only",
        "warmup": WARMUP,
        "timed_passes": TIMED,
        "cpu": platform.processor(),
        "cpu_threads": 1,
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "models": {},
    }
    for name, factory in candidates.items():
        model = factory().eval()
        entry: dict[str, object] = {
            "parameters": int(sum(p.numel() for p in model.parameters())),
            "macs": count_macs(model, INPUT_SIZE),
            "cpu": time_forward(factory(), torch.device("cpu")),
        }
        if torch.cuda.is_available():
            entry["gpu"] = time_forward(factory(), torch.device("cuda"))
        report["models"][name] = entry
        print(name, json.dumps(entry))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
