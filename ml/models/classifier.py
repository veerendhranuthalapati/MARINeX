"""
Stage B Region Classifier for Oil vs Look-alike Discrimination.
Accepts candidate segmented patches/regions and classifies between:
0: Background / Non-oil, 1: True Mineral Oil Spill, 2: Natural Look-alike.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvNeXtBlock(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dwconv = nn.Conv2d(dim, dim, kernel_size=7, padding=3, groups=dim)
        self.norm = nn.BatchNorm2d(dim)
        self.pwconv1 = nn.Linear(dim, 4 * dim)
        self.act = nn.GELU()
        self.pwconv2 = nn.Linear(4 * dim, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.dwconv(x)
        x = self.norm(x)
        x = x.permute(0, 2, 3, 1)  # (N, C, H, W) -> (N, H, W, C)
        x = self.pwconv1(x)
        x = self.act(x)
        x = self.pwconv2(x)
        x = x.permute(0, 3, 1, 2)  # (N, H, W, C) -> (N, C, H, W)
        return residual + x

class OilLookalikeClassifier(nn.Module):
    def __init__(self, in_channels: int = 3, num_classes: int = 3, dims=(32, 64, 128)):
        super().__init__()
        self.num_classes = num_classes

        # Stem
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, dims[0], kernel_size=4, stride=4),
            nn.BatchNorm2d(dims[0]),
        )

        # Stages
        self.stage1 = nn.Sequential(ConvNeXtBlock(dims[0]), ConvNeXtBlock(dims[0]))
        self.down1 = nn.Sequential(nn.Conv2d(dims[0], dims[1], kernel_size=2, stride=2), nn.BatchNorm2d(dims[1]))

        self.stage2 = nn.Sequential(ConvNeXtBlock(dims[1]), ConvNeXtBlock(dims[1]))
        self.down2 = nn.Sequential(nn.Conv2d(dims[1], dims[2], kernel_size=2, stride=2), nn.BatchNorm2d(dims[2]))

        self.stage3 = nn.Sequential(ConvNeXtBlock(dims[2]), ConvNeXtBlock(dims[2]))

        # Head
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(dims[2], 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.25),
            nn.Linear(64, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.stage1(x)
        x = self.down1(x)
        x = self.stage2(x)
        x = self.down2(x)
        x = self.stage3(x)
        x = self.pool(x).flatten(1)
        logits = self.fc(x)
        return logits

    def predict_class(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return torch.argmax(logits, dim=1)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return F.softmax(logits, dim=1)
