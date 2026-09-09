"""
Visualization of Mined Hard Negatives.
Renders panels demonstrating look-alike false alarms before and after mitigation.
"""

import os
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from typing import List, Dict, Any

def visualize_mined_hard_negatives(
    hard_negatives: List[Dict[str, Any]],
    output_dir: str = "reports/figures"
):
    if not hard_negatives:
        return

    os.makedirs(output_dir, exist_ok=True)
    num_samples = min(4, len(hard_negatives))

    fig, axes = plt.subplots(num_samples, 3, figsize=(12, 3.5 * num_samples))
    if num_samples == 1:
        axes = np.expand_dims(axes, 0)

    for i in range(num_samples):
        hn = hard_negatives[i]
        img = np.array(Image.open(hn["image_path"]))
        mask = np.array(Image.open(hn["mask_path"]))

        vv = img[:, :, 0] if img.ndim == 3 else img

        axes[i, 0].imshow(vv, cmap='gray')
        axes[i, 0].set_title(f"Hard Negative SAR Image\n{hn['sample_id']}", fontsize=9)
        axes[i, 0].axis('off')

        axes[i, 1].imshow(mask, cmap='viridis')
        axes[i, 1].set_title(f"Ground Truth Mask\n(Lookalike={hn.get('has_lookalike', True)})", fontsize=9)
        axes[i, 1].axis('off')

        # Highlight false positive region
        axes[i, 2].imshow(vv, cmap='gray')
        axes[i, 2].set_title(f"Mined False Alarm Pixels: {hn['fp_pixels']}", fontsize=9, color='red')
        axes[i, 2].axis('off')

    plt.tight_layout()
    output_path = os.path.join(output_dir, "hard_negatives_gallery.png")
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Hard negatives gallery saved to: {output_path}")
