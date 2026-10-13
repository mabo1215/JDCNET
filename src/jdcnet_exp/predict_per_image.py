"""Per-image class probabilities for trained ResNet-18 X-ray classifiers.

The evaluation pipeline stores only aggregate metrics. This script re-runs
inference for a list of checkpoints and writes one CSV per job with
``patient_id, label, prob_pos`` so that patient-level resampling and paired
tests (e.g. DeLong) can be computed.

Jobs file (CSV): ``job, checkpoint, manifest, split, out`` where ``split`` may
be empty to use every manifest row. The preprocessing matches the evaluation
transform of the training code: resize to the input size and scale to [0, 1].

Usage:
    python -m jdcnet_exp.predict_per_image --jobs jobs.csv [--device cuda]
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models as tvm
from torchvision import transforms


class ResNet18Student(nn.Module):
    """Same parameter layout as the training code's ResNet-18 classifier (``net.*``)."""

    def __init__(self, num_classes: int = 2) -> None:
        super().__init__()
        self.net = tvm.resnet18(weights=None)
        self.net.fc = nn.Linear(self.net.fc.in_features, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def load_rows(manifest: str, split: str) -> list[dict[str, str]]:
    with open(manifest, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if split:
        rows = [r for r in rows if r.get("split") == split]
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--input-size", type=int, default=224)
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    with open(args.jobs, newline="", encoding="utf-8") as fh:
        jobs = list(csv.DictReader(fh))
    by_data: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for job in jobs:
        by_data[(job["manifest"], job.get("split", ""))].append(job)

    tf = transforms.Compose([transforms.Resize((args.input_size, args.input_size)), transforms.ToTensor()])
    device = torch.device(args.device)
    model = ResNet18Student().to(device).eval()
    done = skipped = 0
    for (manifest, split), group in by_data.items():
        todo = [j for j in group if not Path(j["out"]).exists()]
        skipped += len(group) - len(todo)
        if not todo:
            continue
        rows = load_rows(manifest, split)
        images = torch.stack([tf(Image.open(r["image_path"]).convert("RGB")) for r in rows])
        for job in todo:
            state = torch.load(job["checkpoint"], map_location=device)
            model.load_state_dict(state)
            probs = []
            with torch.no_grad():
                for i in range(0, len(images), args.batch_size):
                    logits = model(images[i:i + args.batch_size].to(device))
                    probs.append(torch.softmax(logits.float(), dim=1)[:, 1].cpu())
            p = torch.cat(probs).tolist()
            out = Path(job["out"])
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["patient_id", "label", "split", "prob_pos"])
                for r, pp in zip(rows, p):
                    w.writerow([r["patient_id"], r["label"], r.get("split", ""), f"{pp:.6f}"])
            done += 1
    print(f"jobs done={done} skipped={skipped} total={len(jobs)}")


if __name__ == "__main__":
    main()
