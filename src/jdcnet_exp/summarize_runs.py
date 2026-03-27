from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate best metrics from multiple run directories.")
    parser.add_argument("--runs-root", required=True, help="Directory containing experiment run folders.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    rows: list[dict[str, object]] = []

    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        metrics_path = run_dir / "best_metrics.json"
        if not metrics_path.exists():
            continue
        with open(metrics_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["experiment_name"] = run_dir.name
        rows.append(payload)

    if not rows:
        raise FileNotFoundError(f"No best_metrics.json files found under {runs_root}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"Wrote {output_path}")
