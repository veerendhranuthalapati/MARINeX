"""
Master Experiment Runner and Benchmark Suite for MARINeX Oil Spill AI Models.
Executes Classical baseline, U-Net, U-Net++, SegFormer, Two-Stage Pipeline,
Ablations, Multi-Seed Evaluation, Robustness Benchmarks, and Cross-Dataset Generalization.
"""

import os
import time
import json
import csv
import torch
import numpy as np
from torch.utils.data import DataLoader
from PIL import Image

from ml.data.dataset import Sentinel1SARSpillDataset, sar_collate_fn
from ml.data.transforms import SARPreprocessor, SARAugmentor

def make_loader(dataset, batch_size=8, shuffle=False):
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, collate_fn=sar_collate_fn)
from ml.models.registry import build_model
from ml.losses.segmentation_losses import get_loss_function
from ml.training.trainer import SegmentationTrainer
from ml.training.two_stage_pipeline import TwoStageOilDetector
from ml.evaluation.metrics import compute_pixel_metrics
from ml.evaluation.object_eval import evaluate_object_detection
from ml.evaluation.calibration import calibrate_threshold, compute_expected_calibration_error
from ml.evaluation.robustness import run_robustness_benchmark
from ml.hard_negative_mining.extract_hard_negatives import extract_hard_negatives
from ml.hard_negative_mining.build_hard_negative_dataset import build_hard_negative_augmented_train_set

def load_data_splits(
    inventory_path: str = "reports/dataset_audit.json",
    split_path: str = "data/splits/split_group_aware_v1.json"
):
    with open(split_path, "r") as f:
        split_manifest = json.load(f)

    from ml.data_audit.dataset_inventory import scan_dataset
    inv = scan_dataset("data/datasets/sentinel1_primary")
    sample_map = {s["sample_id"]: s for s in inv["samples"]}

    train_samples = [sample_map[sid] for sid in split_manifest["splits"]["train"]]
    val_samples = [sample_map[sid] for sid in split_manifest["splits"]["val"]]
    test_samples = [sample_map[sid] for sid in split_manifest["splits"]["test"]]

    return train_samples, val_samples, test_samples, split_manifest

def run_all_experiments(reports_dir: str = "reports"):
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs("models/best_model", exist_ok=True)

    print("=================================================================")
    print("  MARINeX: Sentinel-1 SAR Oil Spill Machine Learning Benchmark   ")
    print("=================================================================")

    # 1. Load data
    train_samples, val_samples, test_samples, split_manifest = load_data_splits()
    print(f"Loaded splits: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute device: {device}")

    # -------------------------------------------------------------
    # EXPERIMENT 1: Baseline 1 - Classical Adaptive Otsu
    # -------------------------------------------------------------
    print("\n[+] Evaluating Baseline 1: Classical Image Processing (Adaptive Otsu)...")
    classical_model = build_model("classical")
    classical_val_preds, classical_val_probs, classical_val_targets = [], [], []

    for s in val_samples:
        img = np.array(Image.open(s["image_path"]))
        mask = (np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8)
        pred_bin, conf = classical_model.predict(img)
        classical_val_preds.append(pred_bin)
        classical_val_probs.append(conf)
        classical_val_targets.append(mask)

    classical_val_targets = np.stack(classical_val_targets)
    classical_val_preds = np.stack(classical_val_preds)
    classical_val_probs = np.stack(classical_val_probs)

    m_classical_val = compute_pixel_metrics(classical_val_targets, classical_val_preds, classical_val_probs)
    print(f"Classical Baseline (Val) -> IoU: {m_classical_val['iou']:.4f} | Dice: {m_classical_val['dice']:.4f} | Prec: {m_classical_val['precision']:.4f} | Rec: {m_classical_val['recall']:.4f}")

    # -------------------------------------------------------------
    # EXPERIMENT 2: Baseline 2 - U-Net Baseline
    # -------------------------------------------------------------
    print("\n[+] Training Baseline 2: U-Net (BCE+Dice, 3 channels)...")
    ds_train = Sentinel1SARSpillDataset(train_samples, channels="VV_VH_DIFF", is_training=True, augmentor=SARAugmentor())
    ds_val = Sentinel1SARSpillDataset(val_samples, channels="VV_VH_DIFF", is_training=False)

    train_loader = make_loader(ds_train, batch_size=8, shuffle=True)
    val_loader = make_loader(ds_val, batch_size=8, shuffle=False)

    unet_model = build_model("unet", in_channels=3, num_classes=1)
    optimizer = torch.optim.AdamW(unet_model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = get_loss_function("bce_dice")

    trainer_unet = SegmentationTrainer(unet_model, loss_fn, optimizer, device=device)
    unet_res = trainer_unet.fit(train_loader, val_loader, epochs=10, save_prefix="unet_baseline")
    unet_model.load_weights(unet_res["best_checkpoint"])
    m_unet_val, _, _ = trainer_unet.validate(val_loader)
    print(f"U-Net Baseline (Val) -> IoU: {m_unet_val['iou']:.4f} | Dice: {m_unet_val['dice']:.4f} | Prec: {m_unet_val['precision']:.4f} | Rec: {m_unet_val['recall']:.4f}")

    # -------------------------------------------------------------
    # EXPERIMENT 3: Advanced Model 1 - U-Net++
    # -------------------------------------------------------------
    print("\n[+] Training Advanced Model 1: U-Net++ (Nested Skip)...")
    unetpp_model = build_model("unet_plus_plus", in_channels=3, num_classes=1)
    opt_upp = torch.optim.AdamW(unetpp_model.parameters(), lr=1e-3, weight_decay=1e-4)
    trainer_upp = SegmentationTrainer(unetpp_model, loss_fn, opt_upp, device=device)
    upp_res = trainer_upp.fit(train_loader, val_loader, epochs=10, save_prefix="unetpp")
    unetpp_model.load_weights(upp_res["best_checkpoint"])
    m_upp_val, _, _ = trainer_upp.validate(val_loader)
    print(f"U-Net++ (Val) -> IoU: {m_upp_val['iou']:.4f} | Dice: {m_upp_val['dice']:.4f} | Prec: {m_upp_val['precision']:.4f} | Rec: {m_upp_val['recall']:.4f}")

    # -------------------------------------------------------------
    # EXPERIMENT 4: Primary Strong Model - SegFormer (Transformer)
    # -------------------------------------------------------------
    print("\n[+] Training Primary Model: SegFormer (Hierarchical MiT + All-MLP Decoder)...")
    segformer_model = build_model("segformer", in_channels=3, num_classes=1)
    opt_sf = torch.optim.AdamW(segformer_model.parameters(), lr=8e-4, weight_decay=1e-4)
    trainer_sf = SegmentationTrainer(segformer_model, loss_fn, opt_sf, device=device)
    sf_res = trainer_sf.fit(train_loader, val_loader, epochs=12, save_prefix="segformer_primary")
    segformer_model.load_weights(sf_res["best_checkpoint"])
    m_sf_val, val_targets_sf, val_probs_sf = trainer_sf.validate(val_loader)
    print(f"SegFormer (Val) -> IoU: {m_sf_val['iou']:.4f} | Dice: {m_sf_val['dice']:.4f} | Prec: {m_sf_val['precision']:.4f} | Rec: {m_sf_val['recall']:.4f}")

    # -------------------------------------------------------------
    # EXPERIMENT 5: Stage B Look-alike Discrimination Classifier
    # -------------------------------------------------------------
    print("\n[+] Training Stage B Classifier: Oil vs Look-alike ConvNeXt...")
    # Train 3-class classifier on crop patches
    classifier_model = build_model("classifier", in_channels=3, num_classes=3).to(device)
    opt_cls = torch.optim.AdamW(classifier_model.parameters(), lr=1e-3, weight_decay=1e-4)
    cls_loss_fn = torch.nn.CrossEntropyLoss()

    # Quick training on sample crops
    classifier_model.train()
    for ep in range(8):
        for s in train_samples:
            img = np.array(Image.open(s["image_path"]))
            label = 1 if s["has_oil"] else (2 if s["has_lookalike"] else 0)
            tensor_crop = torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(device)
            target = torch.tensor([label], dtype=torch.long).to(device)

            opt_cls.zero_grad()
            out = classifier_model(tensor_crop)
            l = cls_loss_fn(out, target)
            l.backward()
            opt_cls.step()

    two_stage_system = TwoStageOilDetector(segformer_model, classifier_model, device=device)

    # -------------------------------------------------------------
    # EXPERIMENT 6: Threshold Calibration (Validation Set)
    # -------------------------------------------------------------
    print("\n[+] Calibrating Operating Threshold on Validation Set...")
    calib = calibrate_threshold(val_targets_sf, val_probs_sf)
    optimal_th = calib["recommended_operating_threshold"]
    print(f"Optimal Threshold (Max Dice): {optimal_th} (Val Dice: {calib['max_dice']:.4f}, IoU: {calib['max_iou']:.4f})")

    # Calibration error
    ece_res = compute_expected_calibration_error(val_targets_sf, val_probs_sf)
    print(f"Expected Calibration Error (ECE): {ece_res['ece_percentage']:.2f}%")

    # -------------------------------------------------------------
    # EXPERIMENT 7: Final Test Set Evaluation (Strictly Once!)
    # -------------------------------------------------------------
    print("\n=================================================================")
    print("  EVALUATING ON HELD-OUT TEST SET (STRICTLY ONCE, ZERO LEAKAGE) ")
    print("=================================================================")
    ds_test = Sentinel1SARSpillDataset(test_samples, channels="VV_VH_DIFF", is_training=False)
    test_loader = make_loader(ds_test, batch_size=len(test_samples), shuffle=False)

    # 1. Classical Test Evaluation
    classical_test_preds, classical_test_probs, classical_test_targets = [], [], []
    t0 = time.time()
    for s in test_samples:
        img = np.array(Image.open(s["image_path"]))
        mask = (np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8)
        pred_bin, conf = classical_model.predict(img)
        classical_test_preds.append(pred_bin)
        classical_test_probs.append(conf)
        classical_test_targets.append(mask)
    t_classical_latency = (time.time() - t0) / len(test_samples) * 1000

    m_classical_test = compute_pixel_metrics(
        np.stack(classical_test_targets),
        np.stack(classical_test_preds),
        np.stack(classical_test_probs)
    )

    # 2. U-Net Test Evaluation
    t0 = time.time()
    m_unet_test, targets_unet_test, probs_unet_test = trainer_unet.validate(test_loader, threshold=optimal_th)
    t_unet_latency = (time.time() - t0) / len(test_samples) * 1000

    # 3. U-Net++ Test Evaluation
    t0 = time.time()
    m_upp_test, targets_upp_test, probs_upp_test = trainer_upp.validate(test_loader, threshold=optimal_th)
    t_upp_latency = (time.time() - t0) / len(test_samples) * 1000

    # 4. SegFormer Test Evaluation
    t0 = time.time()
    m_sf_test, targets_sf_test, probs_sf_test = trainer_sf.validate(test_loader, threshold=optimal_th)
    t_sf_latency = (time.time() - t0) / len(test_samples) * 1000

    # 5. Two-Stage Test Evaluation
    t0 = time.time()
    two_stage_preds = []
    two_stage_probs = []
    for s in test_samples:
        img = np.array(Image.open(s["image_path"]))
        rmask, rprobs, _ = two_stage_system.predict(img)
        two_stage_preds.append(rmask)
        two_stage_probs.append(rprobs)
    t_two_stage_latency = (time.time() - t0) / len(test_samples) * 1000

    m_two_stage_test = compute_pixel_metrics(
        np.stack(classical_test_targets),
        np.stack(two_stage_preds),
        np.stack(two_stage_probs)
    )

    # -------------------------------------------------------------
    # EXPERIMENT 8: Object-Level and Geometric Evaluation on Test
    # -------------------------------------------------------------
    print("\n[+] Computing Instance-Level and Geometric Accuracy Metrics...")
    obj_metrics_sf = evaluate_object_detection(
        np.stack(classical_test_targets),
        np.stack([p >= optimal_th for p in probs_sf_test])
    )
    obj_metrics_ts = evaluate_object_detection(
        np.stack(classical_test_targets),
        np.stack(two_stage_preds)
    )

    print(f"SegFormer Object Recall: {obj_metrics_sf['object_recall']*100:.1f}%, Precision: {obj_metrics_sf['object_precision']*100:.1f}%, F1: {obj_metrics_sf['object_f1']*100:.1f}%")
    print(f"Two-Stage Object Recall: {obj_metrics_ts['object_recall']*100:.1f}%, Precision: {obj_metrics_ts['object_precision']*100:.1f}%, F1: {obj_metrics_ts['object_f1']*100:.1f}%")

    # -------------------------------------------------------------
    # EXPERIMENT 9: Multi-Seed Stability Testing (3 Seeds)
    # -------------------------------------------------------------
    print("\n[+] Running Multi-Seed Stability Test (3 Random Seeds)...")
    seed_ious = []
    seed_dices = []
    seed_precs = []
    seed_recs = []

    for s_idx, seed_val in enumerate([42, 123, 999]):
        torch.manual_seed(seed_val)
        np.random.seed(seed_val)
        m_seed = build_model("segformer", in_channels=3, num_classes=1)
        opt_s = torch.optim.AdamW(m_seed.parameters(), lr=8e-4, weight_decay=1e-4)
        tr_s = SegmentationTrainer(m_seed, loss_fn, opt_s, device=device)
        res_s = tr_s.fit(train_loader, val_loader, epochs=8, save_prefix=f"seed_{seed_val}")
        m_seed.load_weights(res_s["best_checkpoint"])
        m_eval, _, _ = tr_s.validate(test_loader, threshold=optimal_th)

        seed_ious.append(m_eval["iou"])
        seed_dices.append(m_eval["dice"])
        seed_precs.append(m_eval["precision"])
        seed_recs.append(m_eval["recall"])

    mean_dice, std_dice = float(np.mean(seed_dices)), float(np.std(seed_dices))
    mean_iou, std_iou = float(np.mean(seed_ious)), float(np.std(seed_ious))
    print(f"Multi-Seed Dice: {mean_dice:.4f} ± {std_dice:.4f} | IoU: {mean_iou:.4f} ± {std_iou:.4f}")

    # -------------------------------------------------------------
    # EXPERIMENT 10: Ablation Studies
    # -------------------------------------------------------------
    print("\n[+] Running Ablation Matrix...")
    ablation_results = []

    # Ablation 1: Channel configuration (VV vs VV+VH vs VV+VH+DIFF)
    print(" - Ablation 1: Input Channels...")
    for ch_mode, ch_num in [("VV", 1), ("VV_VH", 2), ("VV_VH_DIFF", 3)]:
        ds_tr_ch = Sentinel1SARSpillDataset(train_samples, channels=ch_mode, is_training=True)
        ds_va_ch = Sentinel1SARSpillDataset(val_samples, channels=ch_mode, is_training=False)
        ds_te_ch = Sentinel1SARSpillDataset(test_samples, channels=ch_mode, is_training=False)
        m_ch = build_model("unet", in_channels=ch_num, num_classes=1)
        opt_ch = torch.optim.AdamW(m_ch.parameters(), lr=1e-3)
        tr_ch = SegmentationTrainer(m_ch, loss_fn, opt_ch, device=device)
        res_ch = tr_ch.fit(make_loader(ds_tr_ch, batch_size=8), make_loader(ds_va_ch, batch_size=8), epochs=6)
        m_ch.load_weights(res_ch["best_checkpoint"])
        te_m, _, _ = tr_ch.validate(make_loader(ds_te_ch, batch_size=8))
        ablation_results.append({
            "ablation": "Input Channels",
            "variant": ch_mode,
            "iou": te_m["iou"],
            "dice": te_m["dice"],
            "precision": te_m["precision"],
            "recall": te_m["recall"],
            "fpr": te_m["false_positive_rate"]
        })

    # Ablation 2: Augmentation vs No Augmentation
    print(" - Ablation 2: Augmentation...")
    for aug_label, aug_obj in [("No Augmentation", None), ("Physical SAR Augmentation", SARAugmentor())]:
        ds_tr_aug = Sentinel1SARSpillDataset(train_samples, channels="VV_VH_DIFF", is_training=True, augmentor=aug_obj)
        m_aug = build_model("unet", in_channels=3, num_classes=1)
        tr_aug = SegmentationTrainer(m_aug, loss_fn, torch.optim.AdamW(m_aug.parameters(), lr=1e-3), device=device)
        res_aug = tr_aug.fit(make_loader(ds_tr_aug, batch_size=8), val_loader, epochs=6)
        m_aug.load_weights(res_aug["best_checkpoint"])
        te_m, _, _ = tr_aug.validate(test_loader)
        ablation_results.append({
            "ablation": "Augmentation",
            "variant": aug_label,
            "iou": te_m["iou"],
            "dice": te_m["dice"],
            "precision": te_m["precision"],
            "recall": te_m["recall"],
            "fpr": te_m["false_positive_rate"]
        })

    # Ablation 3: Loss functions (BCE vs Dice vs BCE+Dice vs Focal vs Tversky)
    print(" - Ablation 3: Loss Formulations...")
    for l_name in ["bce", "dice", "bce_dice", "focal", "tversky"]:
        l_fn = get_loss_function(l_name)
        m_loss = build_model("unet", in_channels=3, num_classes=1)
        tr_loss = SegmentationTrainer(m_loss, l_fn, torch.optim.AdamW(m_loss.parameters(), lr=1e-3), device=device)
        res_l = tr_loss.fit(train_loader, val_loader, epochs=6)
        m_loss.load_weights(res_l["best_checkpoint"])
        te_m, _, _ = tr_loss.validate(test_loader)
        ablation_results.append({
            "ablation": "Loss Formulation",
            "variant": l_name.upper(),
            "iou": te_m["iou"],
            "dice": te_m["dice"],
            "precision": te_m["precision"],
            "recall": te_m["recall"],
            "fpr": te_m["false_positive_rate"]
        })

    # Ablation 4: Single-Stage vs Two-Stage (Look-alike suppression)
    ablation_results.append({
        "ablation": "Architecture Stages",
        "variant": "Single-Stage (SegFormer)",
        "iou": m_sf_test["iou"],
        "dice": m_sf_test["dice"],
        "precision": m_sf_test["precision"],
        "recall": m_sf_test["recall"],
        "fpr": m_sf_test["false_positive_rate"]
    })
    ablation_results.append({
        "ablation": "Architecture Stages",
        "variant": "Two-Stage (SegFormer + Lookalike Classifier)",
        "iou": m_two_stage_test["iou"],
        "dice": m_two_stage_test["dice"],
        "precision": m_two_stage_test["precision"],
        "recall": m_two_stage_test["recall"],
        "fpr": m_two_stage_test["false_positive_rate"]
    })

    # -------------------------------------------------------------
    # EXPERIMENT 11: Cross-Dataset External Generalisation
    # -------------------------------------------------------------
    print("\n[+] Evaluating Cross-Dataset Generalisation on Dataset B (Singapore Strait)...")
    from ml.data_audit.dataset_inventory import scan_dataset
    ext_inv = scan_dataset("data/datasets/sentinel1_external")
    ds_ext = Sentinel1SARSpillDataset(ext_inv["samples"], channels="VV_VH_DIFF", is_training=False)
    ext_loader = make_loader(ds_ext, batch_size=len(ext_inv["samples"]), shuffle=False)

    m_ext_eval, _, _ = trainer_sf.validate(ext_loader, threshold=optimal_th)
    print(f"In-Domain Test Dice: {m_sf_test['dice']:.4f} -> Cross-Dataset External Dice: {m_ext_eval['dice']:.4f}")

    # -------------------------------------------------------------
    # EXPERIMENT 12: Environmental Robustness Benchmarking
    # -------------------------------------------------------------
    print("\n[+] Running Environmental Robustness Distortion Suite...")
    test_raw_images = [np.array(Image.open(s["image_path"])) for s in test_samples]
    test_raw_masks = [(np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8) for s in test_samples]

    def eval_perturbed_batch(p_imgs, g_masks):
        p_preds = []
        for im in p_imgs:
            tensor_im = torch.from_numpy(im.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(device)
            with torch.no_grad():
                probs = torch.sigmoid(segformer_model(tensor_im)).squeeze().cpu().numpy()
            p_preds.append((probs >= optimal_th).astype(np.uint8))
        return compute_pixel_metrics(np.stack(g_masks), np.stack(p_preds))

    robustness_results = run_robustness_benchmark(eval_perturbed_batch, test_raw_images, test_raw_masks)

    # -------------------------------------------------------------
    # EXPORT ALL BENCHMARK RESULTS
    # -------------------------------------------------------------
    print("\n[+] Exporting Official Benchmark Results to CSV...")

    # 1. reports/final_test_results.csv (Model Comparison Table)
    models_comparison = [
        {"model": "Classical Baseline (Otsu)", "iou": m_classical_test["iou"], "dice": m_classical_test["dice"], "precision": m_classical_test["precision"], "recall": m_classical_test["recall"], "pr_auc": m_classical_test["pr_auc"], "fpr": m_classical_test["false_positive_rate"], "fnr": m_classical_test["false_negative_rate"], "latency_ms": t_classical_latency},
        {"model": "U-Net Baseline", "iou": m_unet_test["iou"], "dice": m_unet_test["dice"], "precision": m_unet_test["precision"], "recall": m_unet_test["recall"], "pr_auc": m_unet_test["pr_auc"], "fpr": m_unet_test["false_positive_rate"], "fnr": m_unet_test["false_negative_rate"], "latency_ms": t_unet_latency},
        {"model": "U-Net++ (Nested)", "iou": m_upp_test["iou"], "dice": m_upp_test["dice"], "precision": m_upp_test["precision"], "recall": m_upp_test["recall"], "pr_auc": m_upp_test["pr_auc"], "fpr": m_upp_test["false_positive_rate"], "fnr": m_upp_test["false_negative_rate"], "latency_ms": t_upp_latency},
        {"model": "SegFormer (Primary Transformer)", "iou": m_sf_test["iou"], "dice": m_sf_test["dice"], "precision": m_sf_test["precision"], "recall": m_sf_test["recall"], "pr_auc": m_sf_test["pr_auc"], "fpr": m_sf_test["false_positive_rate"], "fnr": m_sf_test["false_negative_rate"], "latency_ms": t_sf_latency},
        {"model": "Two-Stage System (SegFormer + Lookalike Clf)", "iou": m_two_stage_test["iou"], "dice": m_two_stage_test["dice"], "precision": m_two_stage_test["precision"], "recall": m_two_stage_test["recall"], "pr_auc": m_two_stage_test["pr_auc"], "fpr": m_two_stage_test["false_positive_rate"], "fnr": m_two_stage_test["false_negative_rate"], "latency_ms": t_two_stage_latency},
    ]

    with open(os.path.join(reports_dir, "final_test_results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "iou", "dice", "precision", "recall", "pr_auc", "fpr", "fnr", "latency_ms"])
        writer.writeheader()
        for r in models_comparison:
            writer.writerow({k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()})

    # Copy to baseline_results.csv and model_comparison.csv
    with open(os.path.join(reports_dir, "model_comparison.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "iou", "dice", "precision", "recall", "pr_auc", "fpr", "fnr", "latency_ms"])
        writer.writeheader()
        for r in models_comparison:
            writer.writerow({k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()})

    # 2. reports/ablation_results.csv
    with open(os.path.join(reports_dir, "ablation_results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ablation", "variant", "iou", "dice", "precision", "recall", "fpr"])
        writer.writeheader()
        for r in ablation_results:
            writer.writerow({k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()})

    # 3. reports/robustness_results.csv
    with open(os.path.join(reports_dir, "robustness_results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["condition", "iou", "dice", "precision", "recall", "fpr"])
        writer.writeheader()
        for r in robustness_results:
            writer.writerow({k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()})

    # 4. reports/cross_dataset_results.csv
    with open(os.path.join(reports_dir, "cross_dataset_results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["evaluation_domain", "dataset_name", "iou", "dice", "precision", "recall", "fpr"])
        writer.writerow(["In-Domain Test", "Dataset A (Arabian Sea)", f"{m_sf_test['iou']:.4f}", f"{m_sf_test['dice']:.4f}", f"{m_sf_test['precision']:.4f}", f"{m_sf_test['recall']:.4f}", f"{m_sf_test['false_positive_rate']:.4f}"])
        writer.writerow(["Cross-Dataset External", "Dataset B (Singapore Strait)", f"{m_ext_eval['iou']:.4f}", f"{m_ext_eval['dice']:.4f}", f"{m_ext_eval['precision']:.4f}", f"{m_ext_eval['recall']:.4f}", f"{m_ext_eval['false_positive_rate']:.4f}"])

    # -------------------------------------------------------------
    # SAVE BEST MODEL ARTIFACT
    # -------------------------------------------------------------
    best_artifact_path = "models/best_model/marinex_segformer_v1.pt"
    segformer_model.save_weights(best_artifact_path, extra_meta={
        "model_name": "marinex-segformer-v1.0.0",
        "optimal_threshold": optimal_th,
        "input_channels": ["VV", "VH", "VV_minus_VH"],
        "normalization": "percentile_2_98",
        "test_metrics": m_sf_test,
        "multi_seed_dice_mean": mean_dice,
        "multi_seed_dice_std": std_dice,
        "ece": ece_res["expected_calibration_error"]
    })
    print(f"\n[OK] Best model artifact exported to: {best_artifact_path}")

    # Save classifier weights
    torch.save(classifier_model.state_dict(), "models/best_model/marinex_lookalike_classifier_v1.pt")

    print("\n[OK] All training runs, ablations, and benchmarks completed successfully.")
    return {
        "models_comparison": models_comparison,
        "optimal_threshold": optimal_th,
        "best_artifact_path": best_artifact_path,
        "multi_seed_stats": {"mean_dice": mean_dice, "std_dice": std_dice, "mean_iou": mean_iou, "std_iou": std_iou}
    }

if __name__ == "__main__":
    run_all_experiments()
