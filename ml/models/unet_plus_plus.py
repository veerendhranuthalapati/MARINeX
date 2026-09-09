"""
Nested U-Net (U-Net++) Architecture for Multi-Scale SAR Slick Delineation.
Implements dense skip pathways between intermediate encoder and decoder feature maps.
"""

import torch
import torch.nn as nn
from ml.models.base import BaseSegmentationModel
from ml.models.unet import DoubleConv

class UNetPlusPlus(BaseSegmentationModel):
    def __init__(self, in_channels: int = 3, num_classes: int = 1, base_features: int = 24):
        super().__init__(model_name="UNetPlusPlus", in_channels=in_channels, num_classes=num_classes)
        bf = base_features

        self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.pool = nn.MaxPool2d(2, 2)

        # Backbone nodes (Level 0, 1, 2, 3, 4)
        self.conv0_0 = DoubleConv(in_channels, bf)
        self.conv1_0 = DoubleConv(bf, bf * 2)
        self.conv2_0 = DoubleConv(bf * 2, bf * 4)
        self.conv3_0 = DoubleConv(bf * 4, bf * 8)

        # Dense nested decoder nodes
        self.conv0_1 = DoubleConv(bf + bf * 2, bf)
        self.conv1_1 = DoubleConv(bf * 2 + bf * 4, bf * 2)
        self.conv2_1 = DoubleConv(bf * 4 + bf * 8, bf * 4)

        self.conv0_2 = DoubleConv(bf * 2 + bf * 2, bf)
        self.conv1_2 = DoubleConv(bf * 4 + bf * 4, bf * 2)

        self.conv0_3 = DoubleConv(bf * 3 + bf * 2, bf)

        self.final = nn.Conv2d(bf, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x0_0 = self.conv0_0(x)
        x1_0 = self.conv1_0(self.pool(x0_0))
        x0_1 = self.conv0_1(torch.cat([x0_0, self.up(x1_0)], 1))

        x2_0 = self.conv2_0(self.pool(x1_0))
        x1_1 = self.conv1_1(torch.cat([x1_0, self.up(x2_0)], 1))
        x0_2 = self.conv0_2(torch.cat([x0_0, x0_1, self.up(x1_1)], 1))

        x3_0 = self.conv3_0(self.pool(x2_0))
        x2_1 = self.conv2_1(torch.cat([x2_0, self.up(x3_0)], 1))
        x1_2 = self.conv1_2(torch.cat([x1_0, x1_1, self.up(x2_1)], 1))
        x0_3 = self.conv0_3(torch.cat([x0_0, x0_1, x0_2, self.up(x1_2)], 1))

        output = self.final(x0_3)
        return output
