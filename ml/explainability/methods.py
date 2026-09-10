"""
Explainable AI methods for the MARINeX SAR segmentation models.

Architecture-appropriate method selection (documented):
  * Occlusion sensitivity — model-agnostic, works for every segmenter
    (U-Net / U-Net++ / SegFormer / classical). Best baseline method: no
    gradient assumptions, directly measures "which input pixels control the
    prediction".
  * Gradient-weighted CAM (Grad-CAM) — appropriate for convolutional feature
    extractors (U-Net, U-Net++). Produces a coarse attribution map from the
    last convolutional feature maps.
  * Attention/activation projection — for SegFormer we do NOT assume raw
    attention weights are explanation; instead we report the decoder feature
    activation. This is documented as a secondary map (Phase 25 directive:
    do not use a popular method blindly).

All methods return an attribution map the same HxW as the input, in [0,1],
plus metadata describing which method/arch derived it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import cv2

import torch.nn.functional as F

from ml.models.base import BaseSegmentationModel


@dataclass
class ExplanationResult:
    method: str
    attribution: np.ndarray          # float32 (H, W), 0..1, input-sized
    model_name: str
    notes: str = ""
    heatmap_png: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "model_name": self.model_name,
            "notes": self.notes,
            "attribution_shape": list(self.attribution.shape),
            "attribution_range": [float(self.attribution.min()), float(self.attribution.max())],
            "heatmap_png": self.heatmap_png,
        }


class OcclusionSensitivity:
    """Perturb square patches and measure drop in predicted oil probability.

    Works for ANY model (no gradients). Grid over the input in (H, W) space.
    """

    def __init__(
        self,
        model: BaseSegmentationModel,
        device: torch.device,
        patch_size: int = 32,
        stride: int = 24,
        fill_value: float = 0.5,
    ):
        self.model = model
        self.device = device
        self.patch_size = patch_size
        self.stride = stride
        self.fill_value = fill_value

    def attributions(self, img_norm: np.ndarray) -> np.ndarray:
        """
        img_norm: preprocessed float32 image (H, W, 3) in [0,1] — SAME normalization
        used at training time (call SARPreprocessor beforehand).
        Returns HxW attribution map in [0,1] (higher = more influential).
        """
        self.model.to(self.device).eval()
        h, w = img_norm.shape[:2]
        base_tensor = self._tensor(img_norm)
        with torch.no_grad():
            base_prob = self._oil_prob(base_tensor)

        attrib = np.zeros((h, w), dtype=np.float32)
        count_map = np.zeros((h, w), dtype=np.float32)
        occ_img = img_norm.copy()

        with torch.no_grad():
            for y in range(0, h - self.patch_size + 1, self.stride):
                for x in range(0, w - self.patch_size + 1, self.stride):
                    occ = occ_img.copy()
                    occ[y:y + self.patch_size, x:x + self.patch_size] = self.fill_value
                    p = self._oil_prob(self._tensor(occ))
                    # importance = drop in predicted oil PRESENCE within the occluded
                    # cell only. Global-mean drops dilute to ~0 on sparse slicks,
                    # so measure the local cell-level logit/probability loss.
                    base_cell = base_prob[y:y + self.patch_size, x:x + self.patch_size]
                    occ_cell = p[y:y + self.patch_size, x:x + self.patch_size]
                    importance = float(np.clip(base_cell - occ_cell, 0.0, None).sum())
                    attrib[y:y + self.patch_size, x:x + self.patch_size] += importance
                    count_map[y:y + self.patch_size, x:x + self.patch_size] += 1.0

        count_map[count_map == 0] = 1.0
        attrib /= count_map
        if attrib.max() > 0:
            attrib = (attrib - attrib.min()) / (attrib.max() - attrib.min())
        return attrib.astype(np.float32)

    def _tensor(self, arr: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(np.ascontiguousarray(arr)).permute(2, 0, 1).unsqueeze(0).float().to(self.device)

    def _oil_prob(self, tensor: torch.Tensor) -> np.ndarray:
        """Return full-resolution oil-class probability map (H, W)."""
        self.model.eval()
        with torch.no_grad():
            logits = self.model(tensor)
        if logits.shape[1] == 1:
            prob = torch.sigmoid(logits)
        else:
            prob = torch.softmax(logits, dim=1)[:, 1:2]
        prob = prob.squeeze().cpu().numpy()
        return prob


class GradCAM:
    """Gradient-weighted class activation mapping on a conv feature map.

    Appropriate for conv-backed segmenters (U-Net, U-Net++): attributions come
    from the gradient of the predicted oil logit w.r.t. the last conv features.
    """

    def __init__(self, model: BaseSegmentationModel, device: torch.device, sample_every: int = 8):
        self.model = model
        self.device = device
        self.sample_every = sample_every  # use every Nth pixel for stable gradients
        self._activations: Dict[str, Any] = {}
        self._registered = False

    def _register_hook(self) -> None:
        if self._registered:
            return
        for name, module in reversed(list(self.model.named_modules())):
            if isinstance(module, torch.nn.Conv2d):
                module.register_forward_hook(self._save_activation(name))
                module.register_full_backward_hook(self._save_gradient(name))

    def _save_activation(self, name: str):
        def hook(module, inp, out):
            self._activations[f"{name}_act"] = out.detach()
        return hook

    def _save_gradient(self, name: str):
        def hook(module, grad_in, grad_out):
            self._activations[f"{name}_grad"] = grad_out[0].detach()
        return hook

    def attributions(self, img_norm: np.ndarray) -> np.ndarray:
        self._register_hook()
        self.model.to(self.device).train()  # train mode so gradients flow
        self._activations.clear()

        tensor = torch.from_numpy(np.ascontiguousarray(img_norm)).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
        tensor.requires_grad_(True)
        logits = self.model(tensor)
        target = logits[:, 0:1] if logits.shape[1] == 1 else logits[:, 1:2]
        self.model.zero_grad()
        target.mean().backward(retain_graph=True)

        # Use the LAST convolutional feature/gradient registered.
        conv_names = [k[:-4] for k in self._activations if k.endswith("_act")]
        conv_names = sorted(set(conv_names))
        if not conv_names:
            raise RuntimeError("No conv layers found for Grad-CAM")
        name = conv_names[-1]
        act = self._activations[f"{name}_act"][0]       # (C, H', W')
        grad = self._activations[f"{name}_grad"][0]     # (C, H', W')

        weights = grad.mean(dim=(1, 2), keepdim=True)   # alpha per channel
        cam = F.relu((weights * act).sum(dim=0)).cpu().numpy()
        if cam.max() > 0:
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        cam32 = cv2.resize(cam.astype(np.float32), (img_norm.shape[1], img_norm.shape[0]),
                           interpolation=cv2.INTER_LINEAR)
        return cam32.astype(np.float32)


def compute_explainability(
    model: BaseSegmentationModel,
    device: torch.device,
    img_norm: np.ndarray,
    methods: Optional[List[str]] = None,
) -> List[ExplanationResult]:
    """Compute a panel of explanation maps for a preprocessed input image."""
    methods = methods or ["occlusion", "gradcam"]
    results: List[ExplanationResult] = []
    for m in methods:
        try:
            if m == "occlusion":
                occ = OcclusionSensitivity(model, device)
                attr = occ.attributions(img_norm)
            elif m == "gradcam":
                gc = GradCAM(model, device)
                attr = gc.attributions(img_norm)
            elif m == "attention":
                # SegFormer decoder-feature projection (documented proxy).
                # Hooks the fused decoder conv (linear_fuse) and projects its mean
                # channel activation to input resolution — a feature-attribution
                # map, NOT raw attention (which is spatially downsampled and has
                # no single canonical spatial layout to draw).
                captured = {}
                feats_hook = None
                target_module = None
                for nm, module in model.named_modules():
                    if nm == "linear_fuse":
                        target_module = module
                        break
                if target_module is None:
                    raise RuntimeError("no linear_fuse decoder module found for attention proxy")
                def _hook(module, inp, out):
                    captured["feats"] = out.detach()
                feats_hook = target_module.register_forward_hook(_hook)
                try:
                    with torch.no_grad():
                        tensor = torch.from_numpy(np.ascontiguousarray(img_norm)).permute(2, 0, 1).unsqueeze(0).float().to(device)
                        model(tensor)
                finally:
                    if feats_hook is not None:
                        feats_hook.remove()
                feats = captured["feats"]
                attr = feats[0].mean(dim=0).cpu().numpy()
                if attr.max() > 0:
                    attr = (attr - attr.min()) / (attr.max() - attr.min())
                attr = cv2.resize(attr.astype(np.float32), (img_norm.shape[1], img_norm.shape[0]),
                                  interpolation=cv2.INTER_LINEAR)
            else:
                raise ValueError(f"unknown explainability method '{m}'")
            results.append(ExplanationResult(
                method=m,
                attribution=attr.astype(np.float32),
                model_name=model.model_name,
            ))
        except Exception as e:  # noqa: BLE001
            results.append(ExplanationResult(
                method=m,
                attribution=np.zeros(img_norm.shape[:2], dtype=np.float32),
                model_name=model.model_name,
                notes=f"failed: {e}",
            ))
    return results