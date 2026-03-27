from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path


def _parse_float_list(raw_value: str) -> list[float]:
    return [float(value.strip()) for value in raw_value.split(",") if value.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and optionally run ablation configs.")
    parser.add_argument("--base-config", required=True, help="Base JSON config path.")
    parser.add_argument("--output-dir", required=True, help="Directory to write generated configs.")
    parser.add_argument("--temperatures", default="2,4,6")
    parser.add_argument("--alphas", default="0.3,0.5,0.7")
    parser.add_argument("--run", action="store_true", help="Run generated configs immediately.")
    args = parser.parse_args()

    temperatures = _parse_float_list(args.temperatures)
    alphas = _parse_float_list(args.alphas)

    with open(args.base_config, "r", encoding="utf-8") as handle:
        base_config = json.load(handle)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_paths: list[Path] = []
    for temperature in temperatures:
        for alpha in alphas:
            config = copy.deepcopy(base_config)
            experiment_name = f"{config['experiment_name']}_t{temperature:g}_a{alpha:g}"
            config["experiment_name"] = experiment_name
            config["output_dir"] = str(Path("runs") / experiment_name)
            config["distillation"]["temperature"] = temperature
            config["distillation"]["alpha"] = alpha

            config_path = output_dir / f"{experiment_name}.json"
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2)
            generated_paths.append(config_path)
            print(f"Wrote {config_path}")

            if args.run:
                subprocess.run(
                    [sys.executable, "-m", "jdcnet_exp.train", "--config", str(config_path)],
                    check=True,
                )

    print(f"Generated {len(generated_paths)} ablation configs.")
