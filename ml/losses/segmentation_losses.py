"""
Loss Functions for Imbalanced SAR Oil Spill Segmentation.
Implements BCE, Dice, Focal, Tversky, and Focal-Tversky loss formulations.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class DiceLoss(nn.Module):
    def __init__(self, smooth: float = 1.0, eps: float = 1e-7):
        super().__init__()
        self.smooth = smooth
        self.eps = eps

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits)
        # Flatten tensors
        probs = probs.view(-1)
        targets = targets.view(-1)

        intersection = (probs * targets).sum()
        dice = (2.0 * intersection + self.smooth) / (probs.sum() + targets.sum() + self.smooth + self.eps)
        return 1.0 - dice

class BCEDiceLoss(nn.Module):
    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5, pos_weight: float = 2.0):
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.pos_weight = torch.tensor([pos_weight])
        self.dice = DiceLoss()

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        pos_weight = self.pos_weight.to(logits.device)
        bce = F.binary_cross_entropy_with_logits(logits.squeeze(1), targets, pos_weight=pos_weight)
        dice = self.dice(logits.squeeze(1), targets)
        return self.bce_weight * bce + self.dice_weight * dice

class FocalLoss(nn.Module):
    def __init__(self, alpha: float = 0.75, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(logits.squeeze(1), targets, reduction='none')
        probs = torch.sigmoid(logits.squeeze(1))
        p_t = probs * targets + (1.0 - probs) * (1.0 - targets)
        alpha_t = self.alpha * targets + (1.0 - self.alpha) * (1.0 - targets)
        focal_weight = alpha_t * torch.pow(1.0 - p_t, self.gamma)
        return (focal_weight * bce).mean()

class TverskyLoss(nn.Module):
    """
    Tversky loss: Generalization of Dice allowing custom weighting of False Positives and False Negatives.
    alpha: FP weight, beta: FN weight (alpha=0.3, beta=0.7 penalizes missed slicks).
    """
    def __init__(self, alpha: float = 0.3, beta: float = 0.7, smooth: float = 1.0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits.squeeze(1)).view(-1)
        targets = targets.view(-1)

        true_pos = (probs * targets).sum()
        false_pos = (probs * (1.0 - targets)).sum()
        false_neg = ((1.0 - probs) * targets).sum()

        tversky = (true_pos + self.smooth) / (true_pos + self.alpha * false_pos + self.beta * false_neg + self.smooth)
        return 1.0 - tversky

class FocalTverskyLoss(nn.Module):
    def __init__(self, alpha: float = 0.3, beta: float = 0.7, gamma: float = 1.33, smooth: float = 1.0):
        super().__init__()
        self.tversky = TverskyLoss(alpha=alpha, beta=beta, smooth=smooth)
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        tversky_loss = self.tversky(logits, targets)
        return torch.pow(tversky_loss, self.gamma)

def get_loss_function(name: str = "bce_dice") -> nn.Module:
    name = name.lower()
    if name == "bce":
        return lambda logits, targets: F.binary_cross_entropy_with_logits(logits.squeeze(1), targets)
    elif name == "dice":
        return DiceLoss()
    elif name == "bce_dice":
        return BCEDiceLoss()
    elif name == "focal":
        return FocalLoss()
    elif name == "tversky":
        return TverskyLoss()
    elif name == "focal_tversky":
        return FocalTverskyLoss()
    else:
        return BCEDiceLoss()
