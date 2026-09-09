"""
SAR-Specific Radiometric Preprocessing and Physical Augmentation Pipeline.
Supports min-max, z-score, robust, and percentile normalization.
Implements physically grounded radar augmentations (multi-look speckle, rotation, reflection).
"""

import numpy as np
import torch
from typing import Dict, Any, Tuple, Optional
import cv2

class SARPreprocessor:
    def __init__(
        self,
        strategy: str = "percentile",
        clip_percentiles: Tuple[float, float] = (2.0, 98.0),
        dataset_mean: Optional[Tuple[float, ...]] = None,
        dataset_std: Optional[Tuple[float, ...]] = None,
    ):
        self.strategy = strategy
        self.clip_percentiles = clip_percentiles
        self.dataset_mean = dataset_mean or (127.5, 127.5, 127.5)
        self.dataset_std = dataset_std or (40.0, 40.0, 40.0)

    def __call__(self, image: np.ndarray) -> np.ndarray:
        img = image.astype(np.float32)

        if self.strategy == "min_max":
            val_min = np.min(img, axis=(0, 1), keepdims=True)
            val_max = np.max(img, axis=(0, 1), keepdims=True)
            denom = np.where(val_max - val_min == 0, 1.0, val_max - val_min)
            return np.ascontiguousarray((img - val_min) / denom)

        elif self.strategy == "percentile":
            low, high = self.clip_percentiles
            p_low = np.percentile(img, low, axis=(0, 1), keepdims=True)
            p_high = np.percentile(img, high, axis=(0, 1), keepdims=True)
            clipped = np.clip(img, p_low, p_high)
            denom = np.where(p_high - p_low == 0, 1.0, p_high - p_low)
            return np.ascontiguousarray((clipped - p_low) / denom)

        elif self.strategy == "z_score":
            mean = np.array(self.dataset_mean, dtype=np.float32)
            std = np.array(self.dataset_std, dtype=np.float32)
            if img.ndim == 2:
                mean = mean[0]
                std = std[0]
            norm = (img - mean) / std
            return np.ascontiguousarray(1.0 / (1.0 + np.exp(-norm)))

        elif self.strategy == "robust":
            med = np.median(img, axis=(0, 1), keepdims=True)
            q25 = np.percentile(img, 25, axis=(0, 1), keepdims=True)
            q75 = np.percentile(img, 75, axis=(0, 1), keepdims=True)
            iqr = np.where(q75 - q25 == 0, 1.0, q75 - q25)
            norm = (img - med) / (iqr * 1.5)
            return np.ascontiguousarray(np.clip(norm * 0.5 + 0.5, 0.0, 1.0))

        else:
            return np.ascontiguousarray(np.clip(img / 255.0, 0.0, 1.0))

class SARAugmentor:
    def __init__(
        self,
        p_flip: float = 0.5,
        p_rotate: float = 0.5,
        p_speckle: float = 0.3,
        p_intensity: float = 0.3,
    ):
        self.p_flip = p_flip
        self.p_rotate = p_rotate
        self.p_speckle = p_speckle
        self.p_intensity = p_intensity

    def __call__(self, image: np.ndarray, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        img = image.copy()
        msk = mask.copy()

        # 1. Horizontal Flip
        if np.random.rand() < self.p_flip:
            img = np.ascontiguousarray(np.fliplr(img))
            msk = np.ascontiguousarray(np.fliplr(msk))

        # 2. Vertical Flip
        if np.random.rand() < self.p_flip:
            img = np.ascontiguousarray(np.flipud(img))
            msk = np.ascontiguousarray(np.flipud(msk))

        # 3. 90-degree Rotations
        if np.random.rand() < self.p_rotate:
            k = np.random.randint(1, 4)
            img = np.ascontiguousarray(np.rot90(img, k))
            msk = np.ascontiguousarray(np.rot90(msk, k))

        # 4. Multiplicative speckle perturbation
        if np.random.rand() < self.p_speckle:
            looks = np.random.uniform(4.0, 6.0)
            noise = np.random.gamma(looks, 1.0 / looks, size=img.shape[:2]).astype(np.float32)
            if img.ndim == 3:
                noise = np.expand_dims(noise, -1)
            img = np.ascontiguousarray(np.clip(img * noise, 0.0, 1.0))

        # 5. Mild intensity scaling
        if np.random.rand() < self.p_intensity:
            scale = np.random.uniform(0.92, 1.08)
            img = np.ascontiguousarray(np.clip(img * scale, 0.0, 1.0))

        return np.ascontiguousarray(img), np.ascontiguousarray(msk)
