from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageFile
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from .config import ExperimentConfig

ImageFile.LOAD_TRUNCATED_IMAGES = True


def _build_transform(image_size: int, is_train: bool) -> transforms.Compose:
    operations: list[object] = [transforms.Resize((image_size, image_size))]
    if is_train:
        operations.extend(
            [
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomAffine(degrees=5, translate=(0.02, 0.02), scale=(0.95, 1.05)),
            ]
        )
    operations.append(transforms.ToTensor())
    return transforms.Compose(operations)


def _load_rgb_image(image_path: str | Path) -> Image.Image:
    return Image.open(Path(image_path)).convert("RGB")


class MedicalImageManifestDataset(Dataset):
    def __init__(
        self,
        manifest: pd.DataFrame,
        image_size: int,
        is_train: bool,
        paired_image_column: str,
        include_paired_image: bool,
    ) -> None:
        self.manifest = manifest.reset_index(drop=True)
        self.transform = _build_transform(image_size=image_size, is_train=is_train)
        self.paired_image_column = paired_image_column
        self.include_paired_image = include_paired_image and paired_image_column in self.manifest.columns

    def __len__(self) -> int:
        return len(self.manifest)

    def __getitem__(self, index: int):
        row = self.manifest.iloc[index]
        image_tensor = self.transform(_load_rgb_image(row["image_path"]))
        label = int(row["label"])
        if not self.include_paired_image:
            return image_tensor, label

        paired_path = row.get(self.paired_image_column, row["image_path"])
        if pd.isna(paired_path):
            paired_path = row["image_path"]
        paired_tensor = self.transform(_load_rgb_image(paired_path))
        return image_tensor, paired_tensor, label


def _filter_manifest(manifest: pd.DataFrame, split: str, modalities: list[str]) -> pd.DataFrame:
    filtered = manifest[manifest["split"] == split]
    if modalities:
        filtered = filtered[filtered["modality"].isin(modalities)]
    return filtered


def load_filtered_manifests(config: ExperimentConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
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

    return train_manifest.reset_index(drop=True), val_manifest.reset_index(drop=True)


def create_dataloaders(config: ExperimentConfig) -> tuple[DataLoader, DataLoader]:
    train_manifest, val_manifest = load_filtered_manifests(config)
    include_paired_image = (
        config.model.paired_input or config.distillation.enabled
    ) and config.data.paired_image_column in train_manifest.columns

    train_dataset = MedicalImageManifestDataset(
        train_manifest,
        image_size=config.model.input_size,
        is_train=True,
        paired_image_column=config.data.paired_image_column,
        include_paired_image=include_paired_image,
    )
    val_dataset = MedicalImageManifestDataset(
        val_manifest,
        image_size=config.model.input_size,
        is_train=False,
        paired_image_column=config.data.paired_image_column,
        include_paired_image=include_paired_image,
    )

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
