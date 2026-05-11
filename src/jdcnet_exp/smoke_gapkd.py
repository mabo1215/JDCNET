"""CPU smoke test for GAP-KD/JDCNet-v2 transfer losses.

The test uses synthetic tensors only. It verifies that confidence-gated KD,
projection-compatible attention alignment, and a one-step student update run
without a GPU or local datasets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback

import torch
import torch.optim as optim

from .config import ModelConfig
from .distillation import (
    distillation_loss,
    projected_attention_loss,
    teacher_confidence_gate,
)
from .models import build_model


def _check(label: str, fn) -> tuple[bool, object | None]:
    try:
        payload = fn()
        print(f"[PASS] {label}")
        return True, payload
    except Exception:
        print(f"[FAIL] {label}")
        traceback.print_exc()
        return False, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a CPU-only GAP-KD smoke test.")
    parser.add_argument("--output-json", default="", help="Optional path for a JSON smoke-test report.")
    args = parser.parse_args()

    torch.manual_seed(7)
    device = torch.device("cpu")
    batch_size = 4
    labels = torch.tensor([0, 1, 0, 1], device=device)
    batch_ct = torch.randn(batch_size, 3, 64, 64, device=device)
    batch_xray = torch.randn(batch_size, 3, 64, 64, device=device)

    results: dict[str, object] = {
        "device": str(device),
        "batch_size": batch_size,
        "status": "failed",
        "checks": {},
    }
    passed: list[bool] = []

    def _build_models():
        teacher = build_model(ModelConfig(name="teacher", num_classes=2, input_size=64, use_dpe=False, use_mhra=False))
        student = build_model(ModelConfig(name="student", num_classes=2, input_size=64, use_dfpn=False))
        return teacher.to(device), student.to(device)

    ok, models = _check("build teacher/student models", _build_models)
    passed.append(ok)
    results["checks"]["build_models"] = ok
    if not ok or models is None:
        _finish(results, passed, args.output_json)
        return

    teacher, student = models
    teacher.eval()
    student.train()

    def _forward_features():
        with torch.no_grad():
            teacher_outputs = teacher.forward_with_features(batch_ct)
        student_outputs = student.forward_with_features(batch_xray)
        assert teacher_outputs["logits"].shape == (batch_size, 2)
        assert student_outputs["logits"].shape == (batch_size, 2)
        return teacher_outputs, student_outputs

    ok, outputs = _check("forward logits and feature maps", _forward_features)
    passed.append(ok)
    results["checks"]["forward_features"] = ok
    if not ok or outputs is None:
        _finish(results, passed, args.output_json)
        return

    teacher_outputs, student_outputs = outputs
    teacher_logits = teacher_outputs["logits"]
    student_logits = student_outputs["logits"]

    def _confidence_gate():
        gate = teacher_confidence_gate(
            teacher_logits=teacher_logits,
            labels=labels,
            threshold=0.0,
            floor=0.05,
            power=1.0,
            requires_correct=False,
        )
        assert gate.shape == (batch_size,)
        assert float(gate.min()) >= 0.0
        assert float(gate.max()) <= 1.0
        return {"mean_gate": float(gate.mean()), "min_gate": float(gate.min()), "max_gate": float(gate.max())}

    ok, gate_payload = _check("confidence gate", _confidence_gate)
    passed.append(ok)
    results["checks"]["confidence_gate"] = ok
    if gate_payload is not None:
        results["gate"] = gate_payload

    gate = teacher_confidence_gate(
        teacher_logits=teacher_logits,
        labels=labels,
        threshold=0.0,
        floor=0.05,
        power=1.0,
        requires_correct=False,
    )

    def _losses():
        kd_loss = distillation_loss(
            student_logits=student_logits,
            teacher_logits=teacher_logits,
            labels=labels,
            temperature=4.0,
            alpha=0.5,
            sample_weights=gate,
        )
        pa_loss = projected_attention_loss(
            student_feature=student_outputs["deepest_feature"],
            teacher_feature=teacher_outputs["deepest_feature"],
            confidence_weights=gate,
        )
        assert torch.isfinite(kd_loss)
        assert torch.isfinite(pa_loss)
        return {"gated_kd_loss": float(kd_loss.detach()), "projected_attention_loss": float(pa_loss.detach())}

    ok, loss_payload = _check("gated KD and projected attention losses", _losses)
    passed.append(ok)
    results["checks"]["losses"] = ok
    if loss_payload is not None:
        results["losses"] = loss_payload

    def _train_step():
        optimizer = optim.AdamW(student.parameters(), lr=1e-3)
        optimizer.zero_grad()
        with torch.no_grad():
            t = teacher.forward_with_features(batch_ct)
        s = student.forward_with_features(batch_xray)
        local_gate = teacher_confidence_gate(
            teacher_logits=t["logits"],
            labels=labels,
            threshold=0.0,
            floor=0.05,
            power=1.0,
            requires_correct=False,
        )
        loss = distillation_loss(
            student_logits=s["logits"],
            teacher_logits=t["logits"],
            labels=labels,
            temperature=4.0,
            alpha=0.5,
            sample_weights=local_gate,
        )
        loss = loss + 0.2 * projected_attention_loss(
            student_feature=s["deepest_feature"],
            teacher_feature=t["deepest_feature"],
            confidence_weights=local_gate,
        )
        loss.backward()
        optimizer.step()
        assert torch.isfinite(loss)
        return {"train_step_loss": float(loss.detach())}

    ok, train_payload = _check("one-step GAP-KD student update", _train_step)
    passed.append(ok)
    results["checks"]["train_step"] = ok
    if train_payload is not None:
        results["train_step"] = train_payload

    _finish(results, passed, args.output_json)


def _finish(results: dict[str, object], passed: list[bool], output_json: str) -> None:
    total = len(passed)
    n_passed = sum(passed)
    results["passed"] = n_passed
    results["total"] = total
    results["status"] = "passed" if n_passed == total else "failed"
    if output_json:
        out = Path(output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print()
    if n_passed == total:
        print(f"GAP-KD smoke test PASSED ({n_passed}/{total}).")
        sys.exit(0)
    print(f"GAP-KD smoke test FAILED ({n_passed}/{total}).")
    sys.exit(1)


if __name__ == "__main__":
    main()
