"""Smoke-test for the JDCNET training pipeline.

Runs a single forward + backward pass on synthetic data (no real images needed)
to verify that the model, loss, and optimiser are all importable and functional.
Designed to run on CPU-only environments (H800 without GPU activated).

Usage:
    python -m jdcnet_exp.smoke_test

Expected output (all lines must appear):
    [PASS] torch import
    [PASS] model import
    [PASS] teacher forward (cpu)
    [PASS] student forward (cpu)
    [PASS] distillation_loss (cpu)
    [PASS] end-to-end train step (cpu)
    Smoke test PASSED – environment is ready for GPU training.
"""
from __future__ import annotations

import sys
import traceback

import torch
import torch.optim as optim


def _check(label: str, fn) -> bool:
    try:
        fn()
        print(f"[PASS] {label}")
        return True
    except Exception:
        print(f"[FAIL] {label}")
        traceback.print_exc()
        return False


def main() -> None:
    results: list[bool] = []

    # ── 1. Basic torch import ──────────────────────────────────────────────────
    results.append(_check("torch import", lambda: torch.zeros(1)))

    # ── 2. Model imports ──────────────────────────────────────────────────────
    from .models import build_model
    from .config import ModelConfig

    def _import_models():
        build_model(ModelConfig(name="teacher", num_classes=2, input_size=64))
        build_model(ModelConfig(name="student", num_classes=2, input_size=64))

    results.append(_check("model import", _import_models))

    # ── 3. Teacher forward pass on CPU ────────────────────────────────────────
    device = torch.device("cpu")
    teacher = build_model(ModelConfig(name="teacher", num_classes=2, input_size=64, use_dpe=True, use_mhra=True)).to(device)
    student = build_model(ModelConfig(name="student", num_classes=2, input_size=64, use_dfpn=True)).to(device)

    batch_ct = torch.randn(2, 3, 64, 64, device=device)
    batch_xray = torch.randn(2, 3, 64, 64, device=device)

    results.append(_check(
        "teacher forward (cpu)",
        lambda: teacher(batch_ct),
    ))

    results.append(_check(
        "student forward (cpu)",
        lambda: student(batch_xray),
    ))

    # ── 4. Distillation loss ──────────────────────────────────────────────────
    from .distillation import distillation_loss

    def _distill_pass():
        teacher.eval()
        with torch.no_grad():
            t_logits = teacher(batch_ct)
        s_logits = student(batch_xray)
        labels = torch.tensor([0, 1], device=device)
        loss = distillation_loss(s_logits, t_logits, labels, temperature=4.0, alpha=0.5)
        assert loss.item() >= 0.0

    results.append(_check("distillation_loss (cpu)", _distill_pass))

    # ── 5. End-to-end backward pass ───────────────────────────────────────────
    def _train_step():
        student.train()
        optimizer = optim.AdamW(student.parameters(), lr=1e-3)
        teacher.eval()
        labels = torch.tensor([0, 1], device=device)

        optimizer.zero_grad()
        with torch.no_grad():
            t_logits = teacher(batch_ct)
        s_logits = student(batch_xray)
        loss = distillation_loss(s_logits, t_logits, labels, temperature=4.0, alpha=0.5)
        loss.backward()
        optimizer.step()
        assert loss.item() >= 0.0

    results.append(_check("end-to-end train step (cpu)", _train_step))

    # ── 6. Data utilities ─────────────────────────────────────────────────────
    def _data_import():
        from .data import create_dataloaders  # noqa: F401
        from .metrics import compute_metrics   # noqa: F401

    results.append(_check("data/metrics imports", _data_import))

    # ── 7. E3: ResNet18 ImageNet pretrained backbone (CPU) ────────────────────
    def _resnet18_pass():
        from .config import ModelConfig
        from .models import ResNet18Classifier
        m = ResNet18Classifier(num_classes=2).to(device)
        m.eval()
        with torch.no_grad():
            out = m(batch_xray)
        assert out.shape == (2, 2)

    results.append(_check("E3 resnet18-imagenet forward (cpu)", _resnet18_pass))

    # ── 8. E4: open_clip available (import-only check, no model download) ─────
    def _open_clip_import():
        import open_clip  # type: ignore  # noqa: F401

    results.append(_check("E4 open_clip import (no download)", _open_clip_import))

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(results)
    total = len(results)
    print()
    if passed == total:
        print(f"Smoke test PASSED ({passed}/{total}) – environment is ready for GPU training.")
        sys.exit(0)
    else:
        print(f"Smoke test FAILED ({passed}/{total}) – fix the [FAIL] items above before enabling GPU.")
        sys.exit(1)


if __name__ == "__main__":
    main()
