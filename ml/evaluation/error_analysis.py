"""
Error Analysis and Visual Results Generator for SAR Oil Spill Models.
Generates multi-panel comparison figures (Original, GT, Baseline, Best Model, Confidence, Error Map)
and compiles the interactive reports/error_analysis.html gallery.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import torch
from typing import List, Dict, Any
from ml.models.registry import build_model
from ml.data.transforms import SARPreprocessor

def generate_error_analysis_and_visual_panels(
    test_samples: List[Dict[str, Any]],
    best_model_path: str = "models/best_model/marinex_segformer_v1.pt",
    reports_dir: str = "reports",
    figures_dir: str = "reports/visual_results"
):
    os.makedirs(figures_dir, exist_ok=True)

    # 1. Load models
    classical = build_model("classical")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    best_model = build_model("segformer", in_channels=3, num_classes=1)
    meta = best_model.load_weights(best_model_path, map_location=device)
    best_model.to(device).eval()
    threshold = meta.get("optimal_threshold", 0.45)

    preprocessor = SARPreprocessor(strategy="percentile")

    html_cards = []

    for idx, s in enumerate(test_samples):
        img_arr = np.array(Image.open(s["image_path"]))
        gt_mask = (np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8)

        # Classical baseline prediction
        class_bin, _ = classical.predict(img_arr)

        # Best model prediction
        norm_img = preprocessor(img_arr)
        t_img = torch.from_numpy(norm_img).permute(2, 0, 1).unsqueeze(0).float().to(device)
        with torch.no_grad():
            probs = torch.sigmoid(best_model(t_img)).squeeze().cpu().numpy()
        pred_bin = (probs >= threshold).astype(np.uint8)

        # Error Map:
        # Green = True Positive, Red = False Positive, Blue = False Negative, Dark = True Negative
        h, w = gt_mask.shape
        error_map = np.zeros((h, w, 3), dtype=np.uint8)
        tp = (gt_mask == 1) & (pred_bin == 1)
        fp = (gt_mask == 0) & (pred_bin == 1)
        fn = (gt_mask == 1) & (pred_bin == 0)

        error_map[tp] = [16, 185, 129]   # Emerald green
        error_map[fp] = [239, 68, 68]     # Red (False alarm)
        error_map[fn] = [59, 130, 246]    # Blue (Missed slick)

        # Compute sample IoU
        intersection = np.sum(tp)
        union = np.sum((gt_mask == 1) | (pred_bin == 1))
        sample_iou = float(intersection / max(union, 1))

        # Generate comparison figure
        fig, axes = plt.subplots(1, 6, figsize=(18, 3.2))

        vv = img_arr[:, :, 0] if img_arr.ndim == 3 else img_arr

        axes[0].imshow(vv, cmap='gray')
        axes[0].set_title("1. Input SAR (VV)", fontsize=9)
        axes[0].axis('off')

        axes[1].imshow(gt_mask, cmap='gray')
        axes[1].set_title(f"2. Ground Truth\n(Oil={s['has_oil']})", fontsize=9)
        axes[1].axis('off')

        axes[2].imshow(class_bin, cmap='gray')
        axes[2].set_title("3. Classical Otsu", fontsize=9)
        axes[2].axis('off')

        axes[3].imshow(pred_bin, cmap='gray')
        axes[3].set_title(f"4. SegFormer (Ours)\nIoU: {sample_iou:.2f}", fontsize=9, color='green' if sample_iou > 0.6 else 'red')
        axes[3].axis('off')

        axes[4].imshow(probs, cmap='magma', vmin=0.0, vmax=1.0)
        axes[4].set_title("5. Confidence Map", fontsize=9)
        axes[4].axis('off')

        axes[5].imshow(error_map)
        axes[5].set_title("6. Error Map\n(Grn=TP, Red=FP, Blu=FN)", fontsize=8)
        axes[5].axis('off')

        plt.tight_layout()
        fig_filename = f"comparison_{s['sample_id']}.png"
        fig_path = os.path.join(figures_dir, fig_filename)
        plt.savefig(fig_path, dpi=160, bbox_inches='tight')
        plt.close()

        # HTML card
        html_cards.append(f"""
        <div class="card">
            <h4>Sample: {s['sample_id']} | Region: {s.get('region', 'Arabian Sea')} | Sample IoU: {sample_iou:.3f}</h4>
            <p>Has Oil: <b>{s['has_oil']}</b> | Has Lookalike: <b>{s.get('has_lookalike', False)}</b> | TP: {int(np.sum(tp))} px | FP: {int(np.sum(fp))} px | FN: {int(np.sum(fn))} px</p>
            <img src="visual_results/{fig_filename}" style="width: 100%; border-radius: 8px;" />
        </div>
        """)

    # Write reports/error_analysis.html
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>MARINeX Oil Spill AI - Error Analysis & Visual Verification Gallery</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #060b13; color: #e2e8f0; padding: 24px; }}
        h1 {{ color: #38bdf8; }}
        .summary {{ background: #0e1a2c; padding: 16px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 24px; }}
        .card {{ background: #0a121e; border: 1px solid #1e293b; padding: 16px; border-radius: 12px; margin-bottom: 20px; }}
        h4 {{ margin-top: 0; color: #f59e0b; }}
        p {{ font-size: 13px; color: #94a3b8; }}
    </style>
</head>
<body>
    <h1>MARINeX Oil Spill AI: Test Set Error Analysis & Qualitative Failure Gallery</h1>
    <div class="summary">
        <p><b>Model Evaluated</b>: SegFormer (marinex-segformer-v1.0.0)</p>
        <p><b>Operating Threshold</b>: {threshold} (Calibrated on Validation set for Max Dice)</p>
        <p><b>Legend</b>: <b>Green</b> = Correctly Detected Oil (TP), <b>Red</b> = False Alarm / Look-alike Leakage (FP), <b>Blue</b> = Missed Spill (FN).</p>
    </div>
    {''.join(html_cards)}
</body>
</html>"""

    html_path = os.path.join(reports_dir, "error_analysis.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Error analysis gallery written to: {html_path}")
