from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from .config import ExperimentConfig


class MedicalImageManifestDataset(Dataset):
    def __init__(self, manifest: pd.DataFrame, image_size: int) -> None:
        self.manifest = manifest.reset_index(drop=True)
        self.transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
            ]
        )

    def __len__(self) -> int:
        return len(self.manifest)

    def __getitem__(self, index: int):
        row = self.manifest.iloc[index]
        image = Image.open(Path(row["image_path"])).convert("RGB")
        image_tensor = self.transform(image)
        label = int(row["label"])
        return image_tensor, label


def _filter_manifest(manifest: pd.DataFrame, split: str, modalities: list[str]) -> pd.DataFrame:
    filtered = manifest[manifest["split"] == split]
    if modalities:
        filtered = filtered[filtered["modality"].isin(modalities)]
    return filtered


def create_dataloaders(config: ExperimentConfig) -> tuple[DataLoader, DataLoader]:
    manifest = pd.read_csv(config.manifest_path)
    required_columns = {"image_path", "label", "modality", "split", "patient_id"}
    missing = required_columns - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest is missing required columns: {sorted(missing)}")

    train_manifest = _filter_manifest(
        manifest,
        split=config.data.train_split,
        modalities=config.data.train_modalities,
    )
    val_manifest = _filter_manifest(
        manifest,
        split=config.data.val_split,
        modalities=config.data.val_modalities,
    )

    if train_manifest.empty:
        raise ValueError("Training manifest is empty after applying filters.")
    if val_manifest.empty:
        raise ValueError("Validation manifest is empty after applying filters.")

    train_dataset = MedicalImageManifestDataset(train_manifest, config.model.input_size)
    val_dataset = MedicalImageManifestDataset(val_manifest, config.model.input_size)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.data.batch_size,
        shuffle=True,
        num_workers=config.data.num_workers,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.data.batch_size,
        shuffle=False,
        num_workers=config.data.num_workers,
    )
    return train_loader, val_loader
