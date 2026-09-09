"""
PyTorch Dataset Implementation for Dual-Polarization Sentinel-1 SAR Oil Spill Data.
Supports flexible channel ablation (VV, VH, VV+VH, VV+VH+DIFF) and multi-task targets.
"""

import os
import json
import torch
from torch.utils.data import Dataset
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple
from ml.data.transforms import SARPreprocessor, SARAugmentor

def sar_collate_fn(batch):
    """Custom collator handling variable-length sample metadata sidecars."""
    images = torch.stack([item[0] for item in batch], dim=0)
    masks = torch.stack([item[1] for item in batch], dim=0)
    metadata = [item[2] for item in batch]
    return images, masks, metadata

class Sentinel1SARSpillDataset(Dataset):
    def __init__(
        self,
        samples: List[Dict[str, Any]],
        channels: str = "VV_VH_DIFF", # 'VV', 'VH', 'VV_VH', 'VV_VH_DIFF'
        task: str = "binary_oil",       # 'binary_oil', 'multiclass'
        preprocessor: Optional[SARPreprocessor] = None,
        augmentor: Optional[SARAugmentor] = None,
        is_training: bool = False,
    ):
        self.samples = samples
        self.channels = channels
        self.task = task
        self.preprocessor = preprocessor or SARPreprocessor(strategy="percentile")
        self.augmentor = augmentor
        self.is_training = is_training

    def __len__(self) -> int:
        return len(self.samples)

    def _select_channels(self, image: np.ndarray) -> np.ndarray:
        if self.channels == "VV":
            return image[:, :, 0:1]
        elif self.channels == "VH":
            return image[:, :, 1:2]
        elif self.channels == "VV_VH":
            return image[:, :, 0:2]
        elif self.channels == "VV_VH_DIFF":
            return image
        else:
            return image

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        s = self.samples[idx]

        # 1. Load image and mask
        raw_img = np.array(Image.open(s["image_path"]))
        raw_mask = np.array(Image.open(s["mask_path"]))

        # 2. Preprocess normalization
        norm_img = self.preprocessor(raw_img)

        # 3. Augmentation (only if training and augmentor provided)
        if self.is_training and self.augmentor:
            norm_img, raw_mask = self.augmentor(norm_img, raw_mask)

        # 4. Channel selection
        sel_img = self._select_channels(norm_img)

        # 5. Format mask according to task
        if self.task == "binary_oil":
            target_mask = (raw_mask == 1).astype(np.float32)
        elif self.task == "multiclass":
            target_mask = np.clip(raw_mask, 0, 2).astype(np.int64)
        else:
            target_mask = (raw_mask == 1).astype(np.float32)

        # Convert to PyTorch tensors with guaranteed contiguous memory
        tensor_img = torch.from_numpy(np.ascontiguousarray(sel_img)).permute(2, 0, 1).contiguous().float()
        tensor_mask = torch.from_numpy(np.ascontiguousarray(target_mask))

        return tensor_img, tensor_mask, s
