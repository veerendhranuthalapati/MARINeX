"""
SegFormer Architecture for Oil Spill vs Look-alike Semantic Segmentation.
Hierarchical Mix-Transformer (MiT) encoder with All-MLP decoder for contextual SAR representation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from ml.models.base import BaseSegmentationModel

class OverlapPatchEmbed(nn.Module):
    def __init__(self, in_channels: int, embed_dim: int, patch_size: int = 7, stride: int = 4):
        super().__init__()
        self.proj = nn.Conv2d(
            in_channels, embed_dim,
            kernel_size=patch_size, stride=stride,
            padding=patch_size // 2
        )
        self.norm = nn.BatchNorm2d(embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)
        x = self.norm(x)
        return x

class EfficientSelfAttention(nn.Module):
    def __init__(self, dim: int, num_heads: int = 4, sr_ratio: int = 2):
        super().__init__()
        self.num_heads = num_heads
        self.scale = (dim // num_heads) ** -0.5

        self.q = nn.Linear(dim, dim, bias=False)
        self.kv = nn.Linear(dim, dim * 2, bias=False)
        self.proj = nn.Linear(dim, dim)

        self.sr_ratio = sr_ratio
        if sr_ratio > 1:
            self.sr = nn.Conv2d(dim, dim, kernel_size=sr_ratio, stride=sr_ratio)
            self.norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor, h: int, w: int) -> torch.Tensor:
        b, n, c = x.shape
        q = self.q(x).reshape(b, n, self.num_heads, c // self.num_heads).permute(0, 2, 1, 3)

        if self.sr_ratio > 1:
            x_ = x.permute(0, 2, 1).reshape(b, c, h, w)
            x_ = self.sr(x_).reshape(b, c, -1).permute(0, 2, 1)
            x_ = self.norm(x_)
            kv = self.kv(x_).reshape(b, -1, 2, self.num_heads, c // self.num_heads).permute(2, 0, 3, 1, 4)
        else:
            kv = self.kv(x).reshape(b, -1, 2, self.num_heads, c // self.num_heads).permute(2, 0, 3, 1, 4)
        k, v = kv[0], kv[1]

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)

        out = (attn @ v).transpose(1, 2).reshape(b, n, c)
        out = self.proj(out)
        return out

class TransformerBlock(nn.Module):
    def __init__(self, dim: int, num_heads: int = 4, sr_ratio: int = 2, mlp_ratio: int = 4):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = EfficientSelfAttention(dim, num_heads=num_heads, sr_ratio=sr_ratio)
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(
            nn.Linear(dim, dim * mlp_ratio),
            nn.GELU(),
            nn.Linear(dim * mlp_ratio, dim),
        )

    def forward(self, x: torch.Tensor, h: int, w: int) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), h, w)
        x = x + self.mlp(self.norm2(x))
        return x

class SegFormer(BaseSegmentationModel):
    def __init__(
        self,
        in_channels: int = 3,
        num_classes: int = 1,
        embed_dims: tuple = (32, 64, 128, 256),
        decoder_dim: int = 128
    ):
        super().__init__(model_name="SegFormer", in_channels=in_channels, num_classes=num_classes)

        # 4 Hierarchical Stages
        self.patch_embed1 = OverlapPatchEmbed(in_channels, embed_dims[0], patch_size=7, stride=4)
        self.block1 = TransformerBlock(embed_dims[0], num_heads=1, sr_ratio=4)

        self.patch_embed2 = OverlapPatchEmbed(embed_dims[0], embed_dims[1], patch_size=3, stride=2)
        self.block2 = TransformerBlock(embed_dims[1], num_heads=2, sr_ratio=2)

        self.patch_embed3 = OverlapPatchEmbed(embed_dims[1], embed_dims[2], patch_size=3, stride=2)
        self.block3 = TransformerBlock(embed_dims[2], num_heads=4, sr_ratio=1)

        self.patch_embed4 = OverlapPatchEmbed(embed_dims[2], embed_dims[3], patch_size=3, stride=2)
        self.block4 = TransformerBlock(embed_dims[3], num_heads=8, sr_ratio=1)

        # All-MLP Decoder
        self.linear_c4 = nn.Linear(embed_dims[3], decoder_dim)
        self.linear_c3 = nn.Linear(embed_dims[2], decoder_dim)
        self.linear_c2 = nn.Linear(embed_dims[1], decoder_dim)
        self.linear_c1 = nn.Linear(embed_dims[0], decoder_dim)

        self.linear_fuse = nn.Sequential(
            nn.Conv2d(decoder_dim * 4, decoder_dim, kernel_size=1, bias=False),
            nn.BatchNorm2d(decoder_dim),
            nn.ReLU(inplace=True),
        )

        self.linear_pred = nn.Conv2d(decoder_dim, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, _, orig_h, orig_w = x.shape

        # Stage 1 (1/4)
        c1 = self.patch_embed1(x)
        _, _, h1, w1 = c1.shape
        c1_flat = c1.flatten(2).transpose(1, 2)
        c1 = self.block1(c1_flat, h1, w1).transpose(1, 2).reshape(b, -1, h1, w1)

        # Stage 2 (1/8)
        c2 = self.patch_embed2(c1)
        _, _, h2, w2 = c2.shape
        c2_flat = c2.flatten(2).transpose(1, 2)
        c2 = self.block2(c2_flat, h2, w2).transpose(1, 2).reshape(b, -1, h2, w2)

        # Stage 3 (1/16)
        c3 = self.patch_embed3(c2)
        _, _, h3, w3 = c3.shape
        c3_flat = c3.flatten(2).transpose(1, 2)
        c3 = self.block3(c3_flat, h3, w3).transpose(1, 2).reshape(b, -1, h3, w3)

        # Stage 4 (1/32)
        c4 = self.patch_embed4(c3)
        _, _, h4, w4 = c4.shape
        c4_flat = c4.flatten(2).transpose(1, 2)
        c4 = self.block4(c4_flat, h4, w4).transpose(1, 2).reshape(b, -1, h4, w4)

        # Decoder MLP
        _c4 = self.linear_c4(c4.flatten(2).transpose(1, 2)).transpose(1, 2).reshape(b, -1, h4, w4)
        _c4 = F.interpolate(_c4, size=(h1, w1), mode='bilinear', align_corners=False)

        _c3 = self.linear_c3(c3.flatten(2).transpose(1, 2)).transpose(1, 2).reshape(b, -1, h3, w3)
        _c3 = F.interpolate(_c3, size=(h1, w1), mode='bilinear', align_corners=False)

        _c2 = self.linear_c2(c2.flatten(2).transpose(1, 2)).transpose(1, 2).reshape(b, -1, h2, w2)
        _c2 = F.interpolate(_c2, size=(h1, w1), mode='bilinear', align_corners=False)

        _c1 = self.linear_c1(c1.flatten(2).transpose(1, 2)).transpose(1, 2).reshape(b, -1, h1, w1)

        _c = self.linear_fuse(torch.cat([_c4, _c3, _c2, _c1], dim=1))
        logits = self.linear_pred(_c)

        # Upsample to original image resolution
        logits = F.interpolate(logits, size=(orig_h, orig_w), mode='bilinear', align_corners=False)
        return logits
