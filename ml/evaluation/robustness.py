"""
Controlled Perturbation and Environmental Robustness Testing Module.
Evaluates model degradation under contrast loss, speckle noise, resolution degradation, and intensity shifts.
"""

import numpy as np
import cv2
from typing import Dict, List, Any, Callable
from ml.evaluation.metrics import compute_pixel_metrics

def perturb_contrast(image: np.ndarray, factor: float = 0.6) -> np.ndarray:
    """Simulates low sea-slick radar contrast during high sea states."""
    mean = np.mean(image, axis=(0, 1), keepdims=True)
    return np.clip((image - mean) * factor + mean, 0, 255).astype(np.uint8)

def perturb_speckle(image: np.ndarray, extra_looks: float = 2.0) -> np.ndarray:
    """Simulates single-look / unmultilooked severe speckle noise."""
    noise = np.random.gamma(extra_looks, 1.0 / extra_looks, size=image.shape[:2])
    if image.ndim == 3:
        noise = np.expand_dims(noise, -1)
    return np.clip(image.astype(np.float32) * noise, 0, 255).astype(np.uint8)

def perturb_resolution(image: np.ndarray, scale: float = 0.5) -> np.ndarray:
    """Downsamples and upsamples to simulate lower resolution sensors (e.g. 20m or 40m)."""
    h, w = image.shape[:2]
    down = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    up = cv2.resize(down, (w, h), interpolation=cv2.INTER_LINEAR)
    return up

def perturb_intensity_shift(image: np.ndarray, shift_db: float = -3.0) -> np.ndarray:
    """Simulates sensor radiometric calibration offset."""
    factor = 10.0 ** (shift_db / 10.0)
    return np.clip(image.astype(np.float32) * factor, 0, 255).astype(np.uint8)

def run_robustness_benchmark(
    eval_fn: Callable[[np.ndarray, np.ndarray], Dict[str, float]],
    test_images: List[np.ndarray],
    test_masks: List[np.ndarray]
) -> List[Dict[str, Any]]:
    """
    Evaluates model across a spectrum of controlled environmental distortions.
    """
    perturbation_conditions = [
        ("Clean Baseline", lambda im: im),
        ("Reduced Contrast (0.6x)", lambda im: perturb_contrast(im, 0.6)),
        ("Severe Contrast (0.4x)", lambda im: perturb_contrast(im, 0.4)),
        ("Enhanced Speckle (L=2.0)", lambda im: perturb_speckle(im, 2.0)),
        ("Resolution Degradation (20m)", lambda im: perturb_resolution(im, 0.5)),
        ("Radiometric Shift (-3dB)", lambda im: perturb_intensity_shift(im, -3.0)),
        ("Radiometric Shift (+3dB)", lambda im: perturb_intensity_shift(im, 3.0)),
    ]

    results = []
    for cond_name, perturb_fn in perturbation_conditions:
        perturbed_images = [perturb_fn(im) for im in test_images]
        metrics = eval_fn(perturbed_images, test_masks)
        results.append({
            "condition": cond_name,
            "iou": metrics["iou"],
            "dice": metrics["dice"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "fpr": metrics["false_positive_rate"]
        })
    return results
