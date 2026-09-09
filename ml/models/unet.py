"""
Standard U-Net Baseline Architecture for SAR Oil Spill Segmentation.
"""

import torch
import torch.nn as nn
from ml.models.base import BaseSegmentationModel

class DoubleConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)

class UNetBaseline(BaseSegmentationModel):
    def __init__(self, in_channels: int = 3, num_classes: int = 1, base_features: int = 32):
        super().__init__(model_name="UNetBaseline", in_channels=in_channels, num_classes=num_classes)
        bf = base_features

        # Encoder
        self.inc = DoubleConv(in_channels, bf)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(bf, bf * 2))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(bf * 2, bf * 4))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(bf * 4, bf * 8))

        # Bottleneck
        self.down4 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(bf * 8, bf * 16))

        # Decoder with skip connections
        self.up1 = nn.ConvTranspose2d(bf * 16, bf * 8, kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv(bf * 16, bf * 8)

        self.up2 = nn.ConvTranspose2d(bf * 8, bf * 4, kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv(bf * 8, bf * 4)

        self.up3 = nn.ConvTranspose2d(bf * 4, bf * 2, kernel_size=2, stride=2)
        self.conv_up3 = DoubleConv(bf * 4, bf * 2)

        self.up4 = nn.ConvTranspose2d(bf * 2, bf, kernel_size=2, stride=2)
        self.conv_up4 = DoubleConv(bf * 2, bf)

        self.outc = nn.Conv2d(bf, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        x = self.up1(x5)
        x = torch.cat([x, x4], dim=1)
        x = self.conv_up1(x)

        x = self.up2(x)
        x = torch.cat([x, x3], dim=1)
        x = self.conv_up2(x)

        x = self.up3(x)
        x = torch.cat([x, x2], dim=1)
        x = self.conv_up3(x)

        x = self.up4(x)
        x = torch.cat([x, x1], dim=1)
        x = self.conv_up4(x)

        logits = self.outc(x)
        return logits
