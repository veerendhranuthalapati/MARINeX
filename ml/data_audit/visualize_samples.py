"""
Visualization Module for Sentinel-1 SAR Oil Spill Samples and Audits.
Generates multi-panel figures showing VV, VH, Polarimetric Difference, Mask, and Overlays.
"""

import os
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

def visualize_dataset_samples(inventory, output_dir="reports/figures", num_samples=6):
    os.makedirs(output_dir, exist_ok=True)
    samples = inventory.get("samples", [])
    if not samples:
        return

    # Select representative samples: some with oil, some with lookalikes, some clean
    oil_samples = [s for s in samples if s["has_oil"] and not s["has_lookalike"]]
    lookalike_samples = [s for s in samples if s["has_lookalike"] and not s["has_oil"]]
    both_samples = [s for s in samples if s["has_oil"] and s["has_lookalike"]]
    clean_samples = [s for s in samples if not s["has_oil"] and not s["has_lookalike"]]

    selected = []
    if oil_samples: selected.extend(oil_samples[:2])
    if lookalike_samples: selected.extend(lookalike_samples[:2])
    if both_samples: selected.extend(both_samples[:1])
    if clean_samples: selected.extend(clean_samples[:1])

    # Pad if needed
    if len(selected) < num_samples:
        for s in samples:
            if s not in selected:
                selected.append(s)
            if len(selected) >= num_samples:
                break

    fig, axes = plt.subplots(len(selected), 5, figsize=(18, 3.5 * len(selected)))
    if len(selected) == 1:
        axes = np.expand_dims(axes, 0)

    # Color map for classes: 0: Navy/Black, 1: Red (Oil), 2: Amber (Lookalike), 3: Cyan (Ship)
    cmap = {
        0: [10, 18, 30],       # Sea
        1: [239, 68, 68],      # Oil (Red)
        2: [245, 158, 11],     # Lookalike (Amber)
        3: [6, 182, 212],      # Ship (Cyan)
        4: [100, 116, 139],    # Land (Gray)
    }

    for idx, s in enumerate(selected):
        img_arr = np.array(Image.open(s["image_path"]))
        mask_arr = np.array(Image.open(s["mask_path"]))

        vv = img_arr[:, :, 0]
        vh = img_arr[:, :, 1]
        diff = img_arr[:, :, 2]

        # Colored mask
        h, w = mask_arr.shape
        colored_mask = np.zeros((h, w, 3), dtype=np.uint8)
        for c, color in cmap.items():
            colored_mask[mask_arr == c] = color

        # Overlay on VV
        vv_rgb = np.stack([vv, vv, vv], axis=-1)
        overlay = (vv_rgb * 0.6 + colored_mask * 0.4).astype(np.uint8)

        # Labels
        label_text = f"Sample: {s['sample_id']}\n"
        if s["has_oil"]: label_text += "[OIL SPILL] "
        if s["has_lookalike"]: label_text += "[LOOKALIKE] "
        if not s["has_oil"] and not s["has_lookalike"]: label_text += "[CLEAN SEA]"

        # Plot VV
        axes[idx, 0].imshow(vv, cmap='gray')
        axes[idx, 0].set_title(f"VV Channel\n{s['sample_id']}", fontsize=9)
        axes[idx, 0].axis('off')

        # Plot VH
        axes[idx, 1].imshow(vh, cmap='gray')
        axes[idx, 1].set_title("VH Channel", fontsize=9)
        axes[idx, 1].axis('off')

        # Plot Pol Diff
        axes[idx, 2].imshow(diff, cmap='magma')
        axes[idx, 2].set_title("Pol Diff (VV - VH)", fontsize=9)
        axes[idx, 2].axis('off')

        # Plot Mask
        axes[idx, 3].imshow(colored_mask)
        axes[idx, 3].set_title("Ground Truth Mask\n(Red=Oil, Amber=Lookalike)", fontsize=9)
        axes[idx, 3].axis('off')

        # Plot Overlay
        axes[idx, 4].imshow(overlay)
        axes[idx, 4].set_title(f"SAR + Mask Overlay\n{label_text}", fontsize=9)
        axes[idx, 4].axis('off')

    plt.tight_layout()
    output_path = os.path.join(output_dir, "sar_sample_audit_panel.png")
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Sample visualization saved to: {output_path}")

if __name__ == "__main__":
    from ml.data_audit.dataset_inventory import scan_dataset
    inv = scan_dataset("data/datasets/sentinel1_primary")
    visualize_dataset_samples(inv)
