"""
Dataset Inventory Module for Sentinel-1 Oil Spill Datasets.
Scans and profiles raw dataset directories, pairings, dimensions, channels, and integrity.
"""

import os
import glob
import json
import hashlib
from typing import Dict, List, Any, Optional
import numpy as np
from PIL import Image

def compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def scan_dataset(root_dir: str) -> Dict[str, Any]:
    """
    Exhaustively scans a dataset root directory without assuming directory names.
    Finds images, masks, and metadata sidecars.
    """
    root_dir = os.path.abspath(root_dir)
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"Dataset root does not exist: {root_dir}")

    # Search for all image-like files
    valid_exts = {'.png', '.tif', '.tiff', '.jpg', '.jpeg', '.npy'}
    all_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_exts:
                all_files.append(os.path.join(root, file))

    # Categorize into images vs masks
    # Convention heuristic: path or filename containing 'mask', 'label', 'target', or 'annotation'
    images = []
    masks = []
    for f in all_files:
        p_lower = f.lower()
        if any(term in p_lower for term in ['mask', 'label', 'target', 'groundtruth']):
            masks.append(f)
        else:
            images.append(f)

    # Match images with masks
    # Create basename mapping
    mask_map = {}
    for m in masks:
        base = os.path.splitext(os.path.basename(m))[0]
        # remove common suffixes if any
        clean_base = base.replace('_mask', '').replace('mask_', '').replace('_label', '')
        mask_map[clean_base] = m

    pairs = []
    unpaired_images = []
    for img_p in images:
        base = os.path.splitext(os.path.basename(img_p))[0]
        clean_base = base.replace('_image', '').replace('img_', '')
        if clean_base in mask_map:
            pairs.append((img_p, mask_map[clean_base], clean_base))
        else:
            unpaired_images.append(img_p)

    # Look for metadata sidecars
    meta_files = glob.glob(os.path.join(root_dir, '**', '*.json'), recursive=True)
    meta_map = {}
    for mf in meta_files:
        base = os.path.splitext(os.path.basename(mf))[0]
        meta_map[base] = mf

    # Profile integrity and properties of paired samples
    corrupted_files = []
    hash_to_files = {}
    sample_stats = []

    for img_path, mask_path, sample_id in pairs:
        try:
            # Read image
            img_arr = np.array(Image.open(img_path))
            mask_arr = np.array(Image.open(mask_path))

            # Image properties
            shape = img_arr.shape
            dtype = str(img_arr.dtype)
            channels = 1 if len(shape) == 2 else shape[2]
            val_min = float(np.min(img_arr))
            val_max = float(np.max(img_arr))
            val_mean = float(np.mean(img_arr))
            val_std = float(np.std(img_arr))
            has_nan = bool(np.isnan(img_arr).any())
            has_inf = bool(np.isinf(img_arr).any())

            # Mask properties
            mask_min = int(np.min(mask_arr))
            mask_max = int(np.max(mask_arr))
            unique_classes = [int(c) for c in np.unique(mask_arr)]
            total_pixels = mask_arr.size
            oil_pixels = int(np.sum(mask_arr == 1))
            lookalike_pixels = int(np.sum(mask_arr == 2))
            oil_ratio = oil_pixels / total_pixels
            lookalike_ratio = lookalike_pixels / total_pixels

            # Duplicate check
            im_hash = compute_file_hash(img_path)
            if im_hash not in hash_to_files:
                hash_to_files[im_hash] = []
            hash_to_files[im_hash].append(img_path)

            # Metadata sidecar
            sidecar_meta = {}
            if sample_id in meta_map:
                try:
                    with open(meta_map[sample_id], 'r') as mf:
                        sidecar_meta = json.load(mf)
                except Exception:
                    pass

            sample_stats.append({
                "sample_id": sample_id,
                "image_path": img_path,
                "mask_path": mask_path,
                "parent_scene_id": sidecar_meta.get("parent_scene_id", "unknown_parent"),
                "region": sidecar_meta.get("region", "unspecified"),
                "dimensions": list(shape[:2]),
                "channels": channels,
                "dtype": dtype,
                "val_min": val_min,
                "val_max": val_max,
                "val_mean": val_mean,
                "val_std": val_std,
                "has_nan": has_nan,
                "has_inf": has_inf,
                "unique_classes": unique_classes,
                "oil_pixels": oil_pixels,
                "lookalike_pixels": lookalike_pixels,
                "oil_ratio": oil_ratio,
                "lookalike_ratio": lookalike_ratio,
                "has_oil": oil_pixels > 0,
                "has_lookalike": lookalike_pixels > 0,
            })

        except Exception as e:
            corrupted_files.append({"image": img_path, "mask": mask_path, "error": str(e)})

    # Find duplicates
    duplicates = [files for files in hash_to_files.values() if len(files) > 1]

    inventory = {
        "dataset_root": root_dir,
        "total_images_found": len(images),
        "total_masks_found": len(masks),
        "paired_samples_count": len(pairs),
        "unpaired_images_count": len(unpaired_images),
        "corrupted_files_count": len(corrupted_files),
        "corrupted_files": corrupted_files,
        "duplicate_groups_count": len(duplicates),
        "duplicate_groups": duplicates,
        "samples": sample_stats
    }
    return inventory

if __name__ == "__main__":
    primary_dir = "data/datasets/sentinel1_primary"
    inv = scan_dataset(primary_dir)
    print(f"Primary inventory scanned: {inv['paired_samples_count']} pairs, {inv['corrupted_files_count']} corrupted.")
