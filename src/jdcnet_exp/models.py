from __future__ import annotations

import os

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class DPEBlock(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.score = nn.Conv2d(channels, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, _, height, width = x.shape
        weights = self.score(x).view(batch_size, -1)
        weights = torch.softmax(weights, dim=1).view(batch_size, 1, height, width)
        return x * weights


class MHRABlock(nn.Module):
    def __init__(self, channels: int, num_heads: int = 4) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(channels)
        self.attention = nn.MultiheadAttention(embed_dim=channels, num_heads=num_heads, batch_first=True)
        self.retain = nn.Linear(channels, channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, channels, height, width = x.shape
        tokens = x.flatten(2).transpose(1, 2)
        norm_tokens = self.norm(tokens)
        attended, _ = self.attention(norm_tokens, norm_tokens, norm_tokens)
        retain_gate = torch.sigmoid(self.retain(norm_tokens))
        fused = (attended * retain_gate + tokens).transpose(1, 2).reshape(batch_size, channels, height, width)
        return fused


class DFPNBlock(nn.Module):
    def __init__(self, in_channels: list[int], out_channels: int) -> None:
        super().__init__()
        self.lateral = nn.ModuleList(
            nn.Conv2d(channels, out_channels, kernel_size=1) for channels in in_channels
        )
        self.output = nn.ModuleList(
            nn.Sequential(
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )
            for _ in in_channels
        )

    def forward(self, features: list[torch.Tensor]) -> torch.Tensor:
        pyramid: list[torch.Tensor] = []
        running: torch.Tensor | None = None
        for feature, lateral, output in zip(reversed(features), reversed(self.lateral), reversed(self.output)):
            reduced = lateral(feature)
            if running is not None:
                reduced = reduced + F.interpolate(running, size=reduced.shape[-2:], mode="nearest")
            running = output(reduced)
            pyramid.append(running)
        pooled = [F.adaptive_avg_pool2d(level, (1, 1)).flatten(1) for level in pyramid]
        return torch.stack(pooled, dim=0).mean(dim=0)


class TeacherEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.stages = nn.ModuleList(
            [
                ConvBlock(3, 32),
                ConvBlock(32, 64),
                ConvBlock(64, 128),
                ConvBlock(128, 256),
            ]
        )

    def forward(self, x: torch.Tensor) -> list[torch.Tensor]:
        features: list[torch.Tensor] = []
        for stage in self.stages:
            x = stage(x)
            features.append(x)
        return features


class StudentEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.stages = nn.ModuleList(
            [
                ConvBlock(3, 32),
                ConvBlock(32, 64),
                ConvBlock(64, 128),
            ]
        )

    def forward(self, x: torch.Tensor) -> list[torch.Tensor]:
        features: list[torch.Tensor] = []
        for stage in self.stages:
            x = stage(x)
            features.append(x)
        return features


class TeacherCNN(nn.Module):
    def __init__(self, num_classes: int, use_dpe: bool = True, use_mhra: bool = True) -> None:
        super().__init__()
        self.encoder = TeacherEncoder()
        self.dpe = DPEBlock(256) if use_dpe else nn.Identity()
        self.mhra = MHRABlock(256) if use_mhra else nn.Identity()
        self.classifier = nn.Linear(256, num_classes)

    def forward_with_features(self, x: torch.Tensor) -> dict[str, torch.Tensor | list[torch.Tensor]]:
        stage_features = self.encoder(x)
        refined_feature = self.mhra(self.dpe(stage_features[-1]))
        embedding = F.adaptive_avg_pool2d(refined_feature, (1, 1)).flatten(1)
        logits = self.classifier(embedding)
        return {
            "logits": logits,
            "stage_features": stage_features,
            "deepest_feature": stage_features[-1],
            "refined_feature": refined_feature,
            "embedding": embedding,
        }

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward_with_features(x)["logits"]


class StudentCNN(nn.Module):
    def __init__(self, num_classes: int, use_dfpn: bool = True) -> None:
        super().__init__()
        self.encoder = StudentEncoder()
        self.use_dfpn = use_dfpn
        self.dfpn = DFPNBlock([32, 64, 128], out_channels=128) if use_dfpn else None
        self.classifier = nn.Linear(128, num_classes)

    def forward_with_features(self, x: torch.Tensor) -> dict[str, torch.Tensor | list[torch.Tensor]]:
        features = self.encoder(x)
        deepest_feature = features[-1]
        if self.use_dfpn and self.dfpn is not None:
            embedding = self.dfpn(features)
        else:
            embedding = F.adaptive_avg_pool2d(deepest_feature, (1, 1)).flatten(1)
        logits = self.classifier(embedding)
        return {
            "logits": logits,
            "stage_features": features,
            "deepest_feature": deepest_feature,
            "embedding": embedding,
        }

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward_with_features(x)["logits"]


class LateFusionCNN(nn.Module):
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.xray_encoder = StudentEncoder()
        self.ct_encoder = StudentEncoder()
        self.classifier = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(128, num_classes),
        )

    def forward(self, xray: torch.Tensor, paired_image: torch.Tensor | None = None) -> torch.Tensor:
        if paired_image is None:
            raise ValueError("LateFusionCNN requires a paired input tensor.")
        xray_feature = F.adaptive_avg_pool2d(self.xray_encoder(xray)[-1], (1, 1)).flatten(1)
        ct_feature = F.adaptive_avg_pool2d(self.ct_encoder(paired_image)[-1], (1, 1)).flatten(1)
        fused = torch.cat([xray_feature, ct_feature], dim=1)
        return self.classifier(fused)


class ResNet18Classifier(nn.Module):
    """E3 baseline: ResNet-18 backbone pre-trained on ImageNet, with classifier head replaced.

    Uses torchvision ResNet-18 (weights=IMAGENET1K_V1). The final FC layer is
    replaced with a new linear head of size `num_classes`. During training all
    parameters are updated (fine-tuning); the frozen-feature variant is not
    used here because the cohort is small enough that full fine-tuning diverges
    less than pure linear probing.
    """

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        import torchvision.models as tvm
        backbone = tvm.resnet18(weights=tvm.ResNet18_Weights.IMAGENET1K_V1)
        in_features = backbone.fc.in_features
        backbone.fc = nn.Linear(in_features, num_classes)
        self.net = backbone

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def forward_with_features(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"logits": self.forward(x)}


class BiomedCLIPClassifier(nn.Module):
    """E4 baseline: BiomedCLIP image encoder (frozen) + linear probe.

    Uses microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224 via open_clip.
    The ViT image encoder is frozen; only the linear head is trained.

    Requires: `pip install open_clip_torch`
    Model will be downloaded to `~/.cache/huggingface` on first use.
    """

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        try:
            import open_clip  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "open_clip_torch is required for BiomedCLIPClassifier. "
                "Install with: pip install open_clip_torch"
            ) from exc

        # Use mirror endpoint by default on restricted networks.
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        os.environ.setdefault("HUGGINGFACE_HUB_ENDPOINT", "https://hf-mirror.com")

        model, _, preprocess = open_clip.create_model_and_transforms(
            "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
        )
        self.encoder = model.visual
        for param in self.encoder.parameters():
            param.requires_grad_(False)

        # Probe the output dimension with a dummy forward pass
        with torch.no_grad():
            dummy = torch.zeros(1, 3, 224, 224)
            feat_dim = self.encoder(dummy).shape[-1]

        self.head = nn.Linear(feat_dim, num_classes)
        self.preprocess = preprocess

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            features = self.encoder(x)
        return self.head(features)

    def forward_with_features(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"logits": self.forward(x)}


def build_model(model_config: ModelConfig) -> nn.Module:
    backbone = getattr(model_config, "backbone", "custom")

    if backbone == "resnet18":
        return ResNet18Classifier(num_classes=model_config.num_classes)

    if backbone == "biomedclip":
        return BiomedCLIPClassifier(num_classes=model_config.num_classes)

    if model_config.name == "teacher":
        return TeacherCNN(
            num_classes=model_config.num_classes,
            use_dpe=model_config.use_dpe,
            use_mhra=model_config.use_mhra,
        )
    if model_config.name == "student":
        return StudentCNN(
            num_classes=model_config.num_classes,
            use_dfpn=model_config.use_dfpn,
        )
    if model_config.name == "late_fusion":
        return LateFusionCNN(num_classes=model_config.num_classes)
    raise ValueError(f"Unsupported model name: {model_config.name}")
