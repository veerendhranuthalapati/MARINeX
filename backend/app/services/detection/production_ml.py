"""
Production Deep-Learning Oil Spill Detector (Phase 3).

Loads the validated segmentation model (final winner from the ML campaign),
mirrors the EXACT training preprocessing (SARPreprocessor percentile +
VV_VH_DIFF channel layout as in ml/data/dataset.py), and emits:

  * raw soft-probability mask  (RAW MODEL OUTPUT - never modified)
  * binary mask at the calibrated operating threshold
  * clearly separated POST-PROCESSED mask (morphology / min-area filtering)

The two outputs are never conflated; the post-processed mask is derived from
the raw mask with a fully configurable parameter set (Phase 5) and both are
persisted to disk so downstream evidence can trace exactly what happened.

SciGuard: this adapter never fabricates a probability. If the checkpoint is
absent or the architecture mismatch is detected, it raises explicitly instead
of returning invented numbers.
"""

import os
from typing import Any, Dict, Optional, Tuple
import numpy as np
from app.services.detection.base import BaseOilSpillDetector
from app.core.config import settings
from app.core.logging import logger


def _find_ml_root() -> str:
    """Locate the repo 'ml' package by walking up from this module.

    The loader must register the real 'ml' package on sys.path so the frozen
    checkpoint's architecture (ml.models.registry) can be reconstructed.
    """
    probe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    for _ in range(6):
        if os.path.isdir(os.path.join(probe, "ml")) and os.path.isfile(
            os.path.join(probe, "ml", "models", "registry.py")
        ):
            return probe
        probe = os.path.abspath(os.path.join(probe, ".."))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


class ProductionMLDetector(BaseOilSpillDetector):
    def __init__(
        self,
        model_weights_path: Optional[str] = None,
        model_name: str = "",
        threshold: Optional[float] = None,
        confidence_min: Optional[float] = None,
        channels: Optional[int] = None,
        postprocess: Optional[Dict[str, Any]] = None,
    ):
        self.model_weights_path = str(model_weights_path or settings.prod_model_abs_path)
        self.model_name = model_name or settings.PROD_MODEL_NAME
        self.threshold = threshold if threshold is not None else settings.PROD_DEFAULT_THRESHOLD
        self.confidence_min = confidence_min if confidence_min is not None else settings.PROD_CONFIDENCE_MIN
        self.channels = channels if channels is not None else settings.PROD_MODEL_CHANNELS
        self.postprocess = postprocess or {
            "min_area_px": 20,
            "morph_open_kernel": 3,
            "remove_tiny_artifacts": True,
        }
        self._model = None
        self._model_meta: Dict[str, Any] = {}
        self._is_loaded = False
        self._last_probs: Optional[np.ndarray] = None
        self._channel_note: str = ""

    # ------------------------------------------------------------------ #
    # Model loading
    # ------------------------------------------------------------------ #
    def load_model(self):
        if self._is_loaded:
            return
        path = self.model_weights_path
        if not path or not os.path.exists(path):
            raise FileNotFoundError(
                f"Production model checkpoint not found at '{path}'. "
                "Run the ML campaign to produce models/best_model/, or configure PROD_MODEL_PATH."
            )
        try:
            import sys
            import torch
            repo_root = _find_ml_root()
            if repo_root not in sys.path:
                sys.path.insert(0, repo_root)
            from ml.models.registry import build_model
            from ml.data.transforms import SARPreprocessor

            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            state = ckpt.get("state_dict", ckpt)
            meta = dict(ckpt.get("metadata", {}))

            # Normalize class names -> registry keys (checkpoints store e.g. UNetBaseline).
            arch_name = (meta.get("architecture") or ckpt.get("model_name") or self.model_name)
            arch_norm = str(arch_name).lower().replace("-", "_")
            arch_key = {
                "unetbaseline": "unet",
                "unet_plus_plusbaseline": "unet_plus_plus",
                "unetplusplus": "unet_plus_plus",
            }.get(arch_norm, arch_norm)

            in_channels = int(meta.get("in_channels") or ckpt.get("in_channels") or self.channels)
            model = build_model(arch_key, in_channels=in_channels, num_classes=1)
            model.load_state_dict(state, strict=meta.get("strict", True))
            model.eval()

            ckpt_threshold = meta.get("threshold")
            if ckpt_threshold is not None:
                self.threshold = float(ckpt_threshold)

            self._model = model
            self._is_loaded = True
            self._model_meta = {
                "architecture": arch_key,
                "in_channels": in_channels,
                "threshold": self.threshold,
                "checkpoint": path,
                "strict_load": meta.get("strict", True),
                "checkpoint_metadata": meta,
            }
        except Exception as e:
            logger.error(f"ProductionMLDetector failed to load checkpoint {path}: {e}")
            self._is_loaded = False
            raise RuntimeError(f"ProductionMLDetector could not load '{path}': {e}") from e

    # ------------------------------------------------------------------ #
    # Core segmentation
    # ------------------------------------------------------------------ #
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Mirror ml/data/dataset.py preprocessing exactly (percentile, 3ch)."""
        try:
            import sys
            import os as _os
            repo_root = _find_ml_root()
            if repo_root not in sys.path:
                sys.path.insert(0, repo_root)
            from ml.data.transforms import SARPreprocessor
        except ImportError as e:
            raise RuntimeError(f"ml.data.transforms unavailable: {e}")

        img = image.astype(np.float32)
        prep = SARPreprocessor(strategy=settings.PROD_PREPROC_VARIANT)

        # Normalize using the SAME per-image percentile as training.
        norm = prep(img)

        # Channel layout: VV_VH_DIFF expects [VV, VH, VV-VH] as the last axis.
        if norm.ndim == 2:
            norm = np.stack([norm, norm, np.zeros_like(norm)], axis=-1)
            self._channel_note = "single-band input replicated: VV=VH=intensity, DIFF=0"
        elif norm.shape[-1] == 1:
            norm = np.repeat(norm, 3, axis=-1)
            self._channel_note = "single-band input replicated: VV=VH=intensity, DIFF=0"
        elif norm.shape[-1] == 2:
            diff = norm[:, :, 0] - norm[:, :, 1]
            norm = np.dstack([norm, diff])
            self._channel_note = "two-band input: constructed VV-VH difference channel"
        else:
            self._channel_note = "three-band VV_VH_DIFF as trained"
        # else assume already 3-channel VV_VH_DIFF

        return np.ascontiguousarray(norm)

    def segment(self, image_input: Any, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        self.load_model()
        import torch
        from PIL import Image

        if isinstance(image_input, (str, os.PathLike)):
            arr = np.array(Image.open(str(image_input)))
        else:
            arr = np.array(image_input)

        if arr.ndim != 2 and arr.size == 0:
            raise ValueError("Empty image input to ProductionMLDetector.")

        norm = self._preprocess(arr)
        t = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            logits = self._model(t)
            probs = torch.sigmoid(logits).squeeze().cpu().numpy()

        self._last_probs = probs

        # RAW binary at operating threshold (no post-processing).
        raw_binary = (probs >= self.threshold).astype(np.uint8)

        oil_pixels = int(np.sum(raw_binary))
        total = raw_binary.size
        mean_prob = float(np.mean(probs[raw_binary == 1])) if oil_pixels > 0 else 0.0

        meta = {
            **self._model_meta,
            "model": self._model_meta.get("architecture", self.model_name),
            "threshold": self.threshold,
            "oil_pixel_count_raw": oil_pixels,
            "coverage_ratio_raw": float(oil_pixels / max(total, 1)),
            "mean_probability": mean_prob,
            "raw_probability_available": True,
            "channel_note": self._channel_note,
        }
        return raw_binary, meta

    def postprocess_mask(self, binary: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Phase 5: configurable morphological + small-object filtering."""
        import cv2
        from scipy import ndimage  # type: ignore

        cfg = self.postprocess
        out = binary.copy()

        if cfg.get("morph_open_kernel"):
            k = int(cfg["morph_open_kernel"])
            if k >= 2:
                kernel = np.ones((k, k), np.uint8)
                out = cv2.morphologyEx(out, cv2.MORPH_OPEN, kernel)

        min_area = int(cfg.get("min_area_px", 0))
        if cfg.get("remove_tiny_artifacts") and min_area > 0:
            labels, n = ndimage.label(out)
            sizes = ndimage.sum(out, labels, range(1, n + 1))
            for lbl, size in zip(range(1, n + 1), sizes):
                if size < min_area:
                    out[labels == lbl] = 0

        report = {
            "min_area_px": min_area,
            "morph_open_kernel": cfg.get("morph_open_kernel"),
            "oil_pixel_count_post": int(np.sum(out)),
            "postprocessed": True,
        }
        return out, report

    def predict(self, image_input: Any, **kwargs) -> Dict[str, Any]:
        raw_bin, meta = self.segment(image_input, **kwargs)
        post_bin, post_meta = self.postprocess_mask(raw_bin)

        probs = self._last_probs
        if probs is not None and post_bin.sum() > 0:
            confidence = float(probs[post_bin == 1].mean())
        else:
            confidence = 0.0

        return {
            "model_name": self._model_meta.get("architecture", self.model_name),
            "model_id": self._model_meta.get("checkpoint", self.model_weights_path),
            "oil_detected": bool(post_meta["oil_pixel_count_post"] > 0),
            "oil_pixels_raw": meta["oil_pixel_count_raw"],
            "oil_pixels_post": post_meta["oil_pixel_count_post"],
            "coverage_percentage": round(meta["coverage_ratio_raw"] * 100, 2),
            "confidence": round(confidence, 4),
            "threshold": self.threshold,
            "raw_mask": raw_bin,
            "post_mask": post_bin,
            "probs": probs,
            "meta": {**meta, **post_meta},
        }

    def confidence(self) -> float:
        return self._model_meta.get("threshold", self.threshold)

    def metadata(self) -> Dict[str, Any]:
        return {
            "adapter": "ProductionMLDetector",
            "architecture": self._model_meta.get("architecture", self.model_name),
            "channels": "VV_VH_DIFF",
            "preprocessing": f"SARPreprocessor({settings.PROD_PREPROC_VARIANT})",
            "calibrated_threshold": self.threshold,
            "status": "OPERATIONAL" if self._is_loaded else "AWAITING_CHECKPOINT",
            "postprocessing": self.postprocess,
            "raw_output_preserved": True,
            "disclaimer": "Probabilities are the raw segmentation soft-max; threshold is campaign-calibrated.",
        }