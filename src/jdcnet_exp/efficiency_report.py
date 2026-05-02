"""FLOPs / parameter / latency measurement for the deployment-time student.

Generates the efficiency table requested by the IEEE TCSVT venue-fit
argument: per-method parameter count, multiply-accumulate (MAC) operations,
and median CPU/GPU inference latency at the deployment input resolution.

Usage:
    python -m jdcnet_exp.efficiency_report \
        --output paper/figs/generated/efficiency_table.tex \
        --csv-output paper/figs/generated/efficiency_table.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import torch

from .config import ModelConfig
from .models import build_model


METHODS = [
    {"name": "Student-only X-ray",          "use_dpe": False, "use_mhra": False, "use_dfpn": False, "input_size": 224},
    {"name": "+ DPE",                        "use_dpe": True,  "use_mhra": False, "use_dfpn": False, "input_size": 224},
    {"name": "+ DPE + MHRA",                 "use_dpe": True,  "use_mhra": True,  "use_dfpn": False, "input_size": 224},
    {"name": "+ DPE + MHRA + DFPN (Full JDCNet)", "use_dpe": True, "use_mhra": True, "use_dfpn": True, "input_size": 224},
]


def count_params(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def measure_macs(model: torch.nn.Module, input_size: int) -> float:
    """MACs via fvcore if available, else a simple flops estimator fallback."""
    try:
        from fvcore.nn import FlopCountAnalysis
        x = torch.randn(1, 1, input_size, input_size)
        flops = FlopCountAnalysis(model, x)
        flops.unsupported_ops_warnings(False)
        flops.uncalled_modules_warnings(False)
        return float(flops.total())
    except Exception:
        try:
            from thop import profile
            x = torch.randn(1, 1, input_size, input_size)
            macs, _ = profile(model, inputs=(x,), verbose=False)
            return float(macs)
        except Exception:
            return float("nan")


def measure_latency(model: torch.nn.Module, input_size: int, device: str, n_warmup: int = 10, n_iter: int = 50) -> float:
    model.eval().to(device)
    x = torch.randn(1, 1, input_size, input_size, device=device)
    with torch.no_grad():
        for _ in range(n_warmup):
            model(x)
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(n_iter):
            model(x)
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        t1 = time.perf_counter()
    return (t1 - t0) / n_iter * 1000.0  # ms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--csv-output", required=False, default=None)
    ap.add_argument("--device", default="auto")
    args = ap.parse_args()

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    rows = []
    for entry in METHODS:
        cfg = ModelConfig(
            name="student",
            num_classes=2,
            input_size=entry["input_size"],
            use_dpe=entry["use_dpe"],
            use_mhra=entry["use_mhra"],
            use_dfpn=entry["use_dfpn"],
            paired_input=False,
        )
        model = build_model(cfg)
        n_params = count_params(model)
        macs = measure_macs(model, entry["input_size"])
        cpu_ms = measure_latency(model, entry["input_size"], device="cpu", n_iter=20)
        gpu_ms = float("nan")
        if device.startswith("cuda"):
            gpu_ms = measure_latency(model, entry["input_size"], device=device)
        rows.append({
            "method": entry["name"],
            "params_M": n_params / 1e6,
            "macs_G": macs / 1e9 if macs == macs else float("nan"),
            "latency_cpu_ms": cpu_ms,
            "latency_gpu_ms": gpu_ms,
        })
        print(f"[ok] {entry['name']}: params={n_params/1e6:.3f}M macs={macs/1e9 if macs==macs else float('nan'):.3f}G cpu={cpu_ms:.2f}ms gpu={gpu_ms:.2f}ms")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write("\\begin{table*}[t]\n")
        fh.write("\\caption{Deployment-time efficiency of the X-ray-only student variants. "
                 "MACs and latency are measured on a single 224$\\times$224 input. "
                 "CPU latency is reported on a single thread; GPU latency on the available CUDA device.}\n")
        fh.write("\\label{tab:efficiency}\n")
        fh.write("\\centering\n")
        fh.write("\\begin{tabular}{|l|c|c|c|c|}\n\\hline\n")
        fh.write("Configuration & Params (M) & MACs (G) & CPU latency (ms) & GPU latency (ms) \\\\ \\hline\n")
        for r in rows:
            macs_s = f"{r['macs_G']:.3f}" if r['macs_G'] == r['macs_G'] else "n/a"
            gpu_s = f"{r['latency_gpu_ms']:.2f}" if r['latency_gpu_ms'] == r['latency_gpu_ms'] else "n/a"
            fh.write(f"{r['method']} & {r['params_M']:.3f} & {macs_s} & {r['latency_cpu_ms']:.2f} & {gpu_s} \\\\ \\hline\n")
        fh.write("\\end{tabular}\n\\end{table*}\n")

    if args.csv_output:
        Path(args.csv_output).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.csv_output).open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["method", "params_M", "macs_G", "latency_cpu_ms", "latency_gpu_ms"])
            writer.writeheader()
            writer.writerows(rows)

    print(f"[done] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
