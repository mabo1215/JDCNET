from __future__ import annotations

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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.encoder(x)
        deepest = self.mhra(self.dpe(features[-1]))
        embedding = F.adaptive_avg_pool2d(deepest, (1, 1)).flatten(1)
        return self.classifier(embedding)


class StudentCNN(nn.Module):
    def __init__(self, num_classes: int, use_dfpn: bool = True) -> None:
        super().__init__()
        self.encoder = StudentEncoder()
        self.use_dfpn = use_dfpn
        self.dfpn = DFPNBlock([32, 64, 128], out_channels=128) if use_dfpn else None
        self.classifier = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.encoder(x)
        if self.use_dfpn and self.dfpn is not None:
            embedding = self.dfpn(features)
        else:
            embedding = F.adaptive_avg_pool2d(features[-1], (1, 1)).flatten(1)
        return self.classifier(embedding)


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


def build_model(model_config: ModelConfig) -> nn.Module:
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
