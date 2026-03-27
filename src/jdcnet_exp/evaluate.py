from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from .artifacts import save_confusion_matrix, write_json
from .config import load_config
from .data import create_dataloaders
from .models import build_model
from .train import evaluate_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate JDCNET experiment scaffold.")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    parser.add_argument("--checkpoint", required=True, help="Path to a model checkpoint.")
    parser.add_argument("--output-dir", help="Optional directory for metrics and confusion matrix artifacts.")
    args = parser.parse_args()

    config = load_config(args.config)
    _, val_loader = create_dataloaders(config)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(config.model).to(device)
    model.load_state_dict(torch.load(Path(args.checkpoint), map_location=device))

    metrics = evaluate_model(model, val_loader, device)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(metrics, output_dir / "metrics.json")
        save_confusion_matrix(metrics["confusion_matrix"], output_dir / "confusion_matrix.png")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
