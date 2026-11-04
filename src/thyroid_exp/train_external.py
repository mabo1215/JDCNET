"""Train a thyroid nodule segmenter and a benign/malignant classifier on a public dataset.

Neither model sees the study cohort during training, so inpainting artefacts in the cohort cannot
inform them. The segmenter is the external localiser used in the feasibility gates. The classifier
is used for a descriptive sensitivity estimate only.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import cv2
import numpy as np
import timm
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, Dataset

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def to_tensor(img_bgr: np.ndarray, size: int) -> torch.Tensor:
    rgb = cv2.cvtColor(cv2.resize(img_bgr, (size, size), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    return torch.from_numpy(((rgb.astype(np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1))


class UNet(nn.Module):
    """ResNet-34 encoder with a light upsampling decoder."""

    def __init__(self) -> None:
        super().__init__()
        self.enc = timm.create_model("resnet34", pretrained=True, features_only=True)
        ch = self.enc.feature_info.channels()
        self.dec = nn.ModuleList()
        prev = ch[-1]
        for c in reversed(ch[:-1]):
            self.dec.append(nn.Sequential(
                nn.Conv2d(prev + c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True),
                nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True),
            ))
            prev = c
        self.head = nn.Conv2d(prev, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feats = self.enc(x)
        y = feats[-1]
        for block, skip in zip(self.dec, reversed(feats[:-1])):
            y = F.interpolate(y, size=skip.shape[-2:], mode="bilinear", align_corners=False)
            y = block(torch.cat([y, skip], 1))
        return F.interpolate(self.head(y), size=x.shape[-2:], mode="bilinear", align_corners=False)


def augment(img: np.ndarray, mask: np.ndarray | None) -> tuple[np.ndarray, np.ndarray | None]:
    if random.random() < 0.5:
        img = img[:, ::-1].copy()
        mask = None if mask is None else mask[:, ::-1].copy()
    h, w = img.shape[:2]
    angle = random.uniform(-10, 10)
    scale = random.uniform(0.85, 1.15)
    tx, ty = random.uniform(-0.08, 0.08) * w, random.uniform(-0.08, 0.08) * h
    mat = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    mat[:, 2] += (tx, ty)
    img = cv2.warpAffine(img, mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if mask is not None:
        mask = cv2.warpAffine(mask, mat, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REFLECT)
    gain = random.uniform(0.75, 1.25)
    gamma = random.uniform(0.75, 1.25)
    img = np.clip(255.0 * (img.astype(np.float32) / 255.0) ** gamma * gain, 0, 255).astype(np.uint8)
    return img, mask


class Pairs(Dataset):
    def __init__(self, img_dir: Path, mask_dir: Path, names: list[str], labels: dict[str, int] | None,
                 size: int, train: bool) -> None:
        self.img_dir, self.mask_dir, self.names, self.labels = img_dir, mask_dir, names, labels
        self.size, self.train = size, train

    def __len__(self) -> int:
        return len(self.names)

    def __getitem__(self, i: int):
        name = self.names[i]
        img = cv2.imread(str(self.img_dir / name), cv2.IMREAD_COLOR)
        mask = cv2.imread(str(self.mask_dir / name), cv2.IMREAD_GRAYSCALE)
        if self.train:
            img, mask = augment(img, mask)
        mask = cv2.resize(mask, (self.size, self.size), interpolation=cv2.INTER_NEAREST)
        label = -1 if self.labels is None else self.labels[name]
        return to_tensor(img, self.size), torch.from_numpy((mask > 127).astype(np.float32))[None], label


def dice_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    p = torch.sigmoid(logits)
    inter = (p * target).sum((1, 2, 3))
    return 1 - ((2 * inter + 1) / (p.sum((1, 2, 3)) + target.sum((1, 2, 3)) + 1)).mean()


@torch.no_grad()
def seg_dice(model: nn.Module, loader: DataLoader, device: str) -> float:
    model.eval()
    scores = []
    for x, y, _ in loader:
        p = (torch.sigmoid(model(x.to(device))) > 0.5).float().cpu()
        inter = (p * y).sum((1, 2, 3))
        scores += ((2 * inter + 1) / (p.sum((1, 2, 3)) + y.sum((1, 2, 3)) + 1)).tolist()
    return float(np.mean(scores))


@torch.no_grad()
def clf_scores(model: nn.Module, loader: DataLoader, device: str) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    probs, labels = [], []
    for x, _, lab in loader:
        probs += torch.sigmoid(model(x.to(device))).squeeze(1).cpu().tolist()
        labels += lab.tolist()
    return np.asarray(probs), np.asarray(labels)


def read_labels(path: Path) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    out = {}
    for row in rows:
        if len(row) < 2:
            continue
        try:
            out[row[0].strip()] = int(float(row[1]))
        except ValueError:
            continue
    return out


def resolve_labels(labels: dict[str, int], names: list[str]) -> dict[str, int]:
    """Map label keys to image filenames, whichever zero-padding the label file uses."""
    by_stem = {}
    for k, v in labels.items():
        stem = Path(k).stem
        by_stem[stem] = v
        if stem.isdigit():
            by_stem[str(int(stem))] = v
    out = {}
    for n in names:
        stem = Path(n).stem
        key = stem if stem in by_stem else (str(int(stem)) if stem.isdigit() else stem)
        if key not in by_stem:
            raise KeyError(f"no label for {n}")
        out[n] = by_stem[key]
    return out


def fold_names(fold_file: Path, names: list[str]) -> tuple[list[str], list[str]]:
    """Return train and validation filenames from an author-provided fold file."""
    data = json.loads(fold_file.read_text())
    val_keys = data.get("val") or data.get("valid") or data.get("validation")
    by_stem = {Path(n).stem: n for n in names}
    val = []
    for k in val_keys:
        stem = Path(str(k)).stem
        if stem in by_stem:
            val.append(by_stem[stem])
        elif stem.isdigit():
            hit = next((n for s, n in by_stem.items() if s.isdigit() and int(s) == int(stem)), None)
            if hit:
                val.append(hit)
    val_set = set(val)
    if not val_set:
        raise ValueError("validation split could not be matched to image names")
    return [n for n in names if n not in val_set], sorted(val_set)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, default=320)
    ap.add_argument("--seg-epochs", type=int, default=40)
    ap.add_argument("--clf-epochs", type=int, default=25)
    ap.add_argument("--batch", type=int, default=14)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.out.mkdir(parents=True, exist_ok=True)

    tv_img, tv_mask = args.data / "trainval-image", args.data / "trainval-mask"
    te_img, te_mask = args.data / "test-image", args.data / "test-mask"
    tv_names = sorted(p.name for p in tv_img.iterdir())
    te_names = sorted(p.name for p in te_img.iterdir())
    tr, va = fold_names(args.data / "tn3k-trainval-fold0.json", tv_names)
    print(f"train={len(tr)} val={len(va)} test={len(te_names)}", flush=True)

    tv_labels = resolve_labels(read_labels(args.data / "label4trainval.csv"), tv_names)
    te_labels = resolve_labels(read_labels(args.data / "label4test.csv"), te_names)

    def loader(img, mask, names, labels, train):
        ds = Pairs(img, mask, names, labels, args.size, train)
        return DataLoader(ds, batch_size=args.batch, shuffle=train, num_workers=6, pin_memory=True, drop_last=train)

    # Segmentation
    model = UNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.seg_epochs)
    scaler = torch.amp.GradScaler("cuda")
    tr_l, va_l, te_l = loader(tv_img, tv_mask, tr, None, True), loader(tv_img, tv_mask, va, None, False), loader(te_img, te_mask, te_names, None, False)
    best = -1.0
    for ep in range(args.seg_epochs):
        model.train()
        for x, y, _ in tr_l:
            x, y = x.to(device), y.to(device)
            with torch.amp.autocast("cuda"):
                logits = model(x)
                loss = F.binary_cross_entropy_with_logits(logits, y) + dice_loss(logits, y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        sched.step()
        d = seg_dice(model, va_l, device)
        if d > best:
            best = d
            torch.save(model.state_dict(), args.out / "seg.pt")
        print(f"seg epoch {ep + 1}/{args.seg_epochs} val_dice={d:.4f} best={best:.4f}", flush=True)
    model.load_state_dict(torch.load(args.out / "seg.pt"))
    test_dice = seg_dice(model, te_l, device)
    print(f"seg test_dice={test_dice:.4f}", flush=True)
    del model, opt, scaler
    torch.cuda.empty_cache()

    # Classification
    pos = sum(tv_labels[n] for n in tr)
    neg = len(tr) - pos
    clf = timm.create_model("resnet34", pretrained=True, num_classes=1).to(device)
    opt = torch.optim.AdamW(clf.parameters(), lr=1e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.clf_epochs)
    scaler = torch.amp.GradScaler("cuda")
    weight = torch.tensor([neg / max(pos, 1)], device=device)
    tr_l = loader(tv_img, tv_mask, tr, tv_labels, True)
    va_l = loader(tv_img, tv_mask, va, tv_labels, False)
    te_l = loader(te_img, te_mask, te_names, te_labels, False)
    best = -1.0
    for ep in range(args.clf_epochs):
        clf.train()
        for x, _, lab in tr_l:
            x, lab = x.to(device), lab.float().to(device)
            with torch.amp.autocast("cuda"):
                loss = F.binary_cross_entropy_with_logits(clf(x).squeeze(1), lab, pos_weight=weight)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        sched.step()
        p, y = clf_scores(clf, va_l, device)
        auc = roc_auc_score(y, p)
        if auc > best:
            best = auc
            torch.save(clf.state_dict(), args.out / "clf.pt")
        print(f"clf epoch {ep + 1}/{args.clf_epochs} val_auc={auc:.4f} best={best:.4f}", flush=True)
    clf.load_state_dict(torch.load(args.out / "clf.pt"))
    pv, yv = clf_scores(clf, va_l, device)
    pt, yt = clf_scores(clf, te_l, device)

    # Operating points are fixed on validation data only, then carried to test and to the cohort.
    neg_scores = np.sort(pv[yv == 0])
    thr_spec80 = float(neg_scores[int(0.80 * len(neg_scores))])
    pos_scores = np.sort(pv[yv == 1])
    thr_sens90 = float(pos_scores[int(0.10 * len(pos_scores))])
    summary = dict(
        seg_test_dice=test_dice,
        clf_val_auc=float(roc_auc_score(yv, pv)), clf_test_auc=float(roc_auc_score(yt, pt)),
        thr_spec80=thr_spec80, thr_sens90=thr_sens90,
        test_sens_at_spec80=float((pt[yt == 1] >= thr_spec80).mean()),
        test_spec_at_spec80=float((pt[yt == 0] < thr_spec80).mean()),
        test_sens_at_sens90=float((pt[yt == 1] >= thr_sens90).mean()),
        test_spec_at_sens90=float((pt[yt == 0] < thr_sens90).mean()),
        train_pos=pos, train_neg=neg, test_pos=int(yt.sum()), test_neg=int((yt == 0).sum()),
    )
    (args.out / "external_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
