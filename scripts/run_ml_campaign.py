"""
MARINeX Scientific ML Campaign (SIH26143).
==========================================

Reproducible, protocol-driven experiment campaign that follows the strict
scientific pipeline:

  1. Load group-aware leakage-free split (train/val/test).
  2. Choose architecture / channels / loss / augmentation / preprocessing
     using VALIDATION ONLY.
  3. Hard-negative mining from train+val (never test) + retrain comparison.
  4. Two-stage (stage-A segmentation + stage-B look-alike classifier).
  5. Threshold sweep + temperature calibration on validation.
  6. FREEZE the configuration, then evaluate the held-out TEST set once.
  7. Multi-seed stability, object-level metrics, area accuracy.
  8. Robustness + cross-dataset generalization (no merging).

Nothing is fabricated. Every number in reports/*.csv comes from a real run.
Final test is only touched after all decisions are frozen.

Usage:
    .venv\\Scripts\\python scripts/run_ml_campaign.py [--quick]
    # --quick runs reduced epochs for fast iteration.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader

from ml.data.dataset import Sentinel1SARSpillDataset, sar_collate_fn
from ml.data.transforms import SARPreprocessor, SARAugmentor
from ml.data.leakage_detection import detect_data_leakage
from ml.data_audit.dataset_inventory import scan_dataset
from ml.models.registry import build_model
from ml.losses.segmentation_losses import get_loss_function
from ml.training.trainer import SegmentationTrainer
from ml.training.two_stage_pipeline import (
    TwoStageOilDetector, prepare_stage_b_crops_for_training,
    train_stage_b_classifier, DEFAULT_MIN_AREA,
)
from ml.evaluation.metrics import compute_pixel_metrics
from ml.evaluation.object_eval import evaluate_object_detection
from ml.evaluation.calibration import (
    calibrate_threshold, compute_expected_calibration_error,
    fit_temperature_scaling, recalibrate_probabilities, compute_brier_score,
)
from ml.evaluation.robustness import run_robustness_benchmark
from ml.hard_negative_mining.extract_hard_negatives import extract_hard_negatives
from ml.hard_negative_mining.build_hard_negative_dataset import build_hard_negative_augmented_train_set

SPLIT_PATH = "data/splits/split_group_aware_v1.json"
PRIMARY_ROOT = "data/datasets/sentinel1_primary"
EXTERNAL_ROOT = "data/datasets/sentinel1_external"
CHKPT_DIR = Path("models/campaign")
REPORTS = Path("reports")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PREP = SARPreprocessor(strategy="percentile")

# Cap intra-op threads on CPU VMs so torch does not explode thread-local
# buffers (a key contributor to the silent OOM kills seen at multi-seed).
if DEVICE.type == "cpu":
    torch.set_num_threads(min(8, os.cpu_count() or 8))

# CPU-budgeted training epochs (UNet/UNet++ cost ~45-55 s/epoch here; SegFormer ~6 s).
ARCH_EPOCHS = {"unet": 8, "unet_plus_plus": 8, "segformer": 12}
ABLATION_EPOCHS = 5
HN_EPOCHS = 8
MULTISEED_EPOCHS = 6

# Populated once at load_split() so helper calls without sample_set share the same splits.
_TRAIN = []
_VAL = []


def set_seed(seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_split(split_path=SPLIT_PATH, root=PRIMARY_ROOT):
    global _TRAIN, _VAL
    with open(split_path, "r", encoding="utf-8") as f:
        split = json.load(f)
    inv = scan_dataset(root)
    smap = {s["sample_id"]: s for s in inv["samples"]}
    train = [smap[sid] for sid in split["splits"]["train"]]
    val = [smap[sid] for sid in split["splits"]["val"]]
    test = [smap[sid] for sid in split["splits"]["test"]]
    _TRAIN, _VAL = train, val
    return train, val, test, split, inv


def make_loader(samples, channels, is_training=False, augmentor=None, preprocessor=None, batch_size=8, shuffle=None):
    ds = Sentinel1SARSpillDataset(
        samples, channels=channels, is_training=is_training,
        augmentor=augmentor, preprocessor=preprocessor or PREP,
    )
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle if shuffle is not None else is_training,
                      collate_fn=sar_collate_fn)


def train_model(model_key, channels, loss_name, augment, epochs, seed, preprocessor=None, sample_set=None,
                lr=8e-4, weight_decay=1e-4, tag="m"):
    set_seed(seed)
    if sample_set is None:
        sample_set = {"train": _TRAIN, "val": _VAL}
    in_ch = {"VV": 1, "VH": 1, "VV_VH": 2, "VV_VH_DIFF": 3}[channels]
    ckpt_path = CHKPT_DIR / f"{tag}_best.pt"
    done_flag = CHKPT_DIR / f"{tag}.done"

    # Resume: skip re-training a config whose done flag exists.
    model = build_model(model_key, in_channels=in_ch, num_classes=1)
    loss_fn = get_loss_function(loss_name)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    trainer = SegmentationTrainer(model, loss_fn, opt, device=DEVICE,
                                  checkpoint_dir=str(CHKPT_DIR))
    t_samples = sample_set["train"]
    v_samples = sample_set["val"]
    aug = SARAugmentor() if augment else None
    t_loader = make_loader(t_samples, channels, is_training=True, augmentor=aug, preprocessor=preprocessor)
    v_loader = make_loader(v_samples, channels, is_training=False, preprocessor=preprocessor)

    if done_flag.exists() and ckpt_path.exists():
        print(f"  [resume] loading {tag}: checkpoint exists, skipping training")
        model.load_weights(str(ckpt_path))
        metrics, targets, probs = trainer.validate(v_loader)
        return model, trainer, {"best_checkpoint": str(ckpt_path)}, metrics, targets, probs

    epochs = 3 if args.quick else epochs
    res = trainer.fit(t_loader, v_loader, epochs=epochs, early_stopping_patience=4, save_prefix=tag)
    model.load_weights(res["best_checkpoint"])
    metrics, targets, probs = trainer.validate(v_loader)
    done_flag.touch()
    return model, trainer, res, metrics, targets, probs


def eval_on_split(model, samples, channels="VV_VH_DIFF", threshold=0.5):
    model.eval()
    loader = make_loader(samples, channels, is_training=False, batch_size=len(samples) or 16)
    _, targets, probs = run_validate(model, loader)
    preds = (probs >= threshold).astype(np.uint8)
    px = compute_pixel_metrics(targets, preds, probs)
    obj = evaluate_object_detection(targets, preds)
    ece = compute_expected_calibration_error(targets, probs)
    brier = compute_brier_score(targets, probs)
    return px, obj, ece, brier, targets, probs


def run_validate(model, loader):
    model.eval()
    all_t, all_p = [], []
    with torch.no_grad():
        for images, masks, _ in loader:
            images = images.to(DEVICE)
            logits = model(images)
            probs = torch.sigmoid(logits.squeeze(1)).cpu().numpy()
            all_p.append(probs)
            all_t.append(masks.numpy().astype(np.uint8))
    return None, np.concatenate(all_t), np.concatenate(all_p)


def measure_latency(model, n=8):
    model.eval()
    x = torch.randn(1, 3, 256, 256).to(DEVICE)
    with torch.no_grad():
        for _ in range(3):
            model(x)
        t0 = time.time()
        for _ in range(n):
            model(x)
        return (time.time() - t0) / n * 1000.0


def infer_prob(model, img_arr):
    norm = PREP(img_arr)
    t = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        p = torch.sigmoid(model(t)).squeeze().cpu().numpy()
    h, w = img_arr.shape[:2]
    if p.shape != (h, w):
        import cv2
        p = cv2.resize(p, (w, h), interpolation=cv2.INTER_LINEAR)
    return p


def main():
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    os.makedirs(CHKPT_DIR, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)

    print("=" * 72)
    print("  MARINeX ML Scientific Campaign — SIH26143")
    print(f"  device={DEVICE}  quick={args.quick}")
    print("=" * 72)

    # -----------------------------------------------------------------
    # 1. DATA + LEAKAGE VERIFICATION
    # -----------------------------------------------------------------
    train, val, test, split, inv = load_split()
    leak = detect_data_leakage(inv, split)
    print(f"[1] split train/val/test = {len(train)}/{len(val)}/{len(test)}")
    print(f"[1] leakage: {leak['verification_status']}")
    assert not leak["leakage_detected"], "STOP: leakage detected."

    sample_set = {"train": train, "val": val, "test": test}

    # =================================================================
    # ARCHITECTURE SELECTION ON VALIDATION
    # =================================================================
    print("\n[2] Architecture selection on VALIDATION only ...")
    arch_results = []
    arch_models = {}
    for key in ["unet", "unet_plus_plus", "segformer"]:
        m, tr, res, val_m, val_t, val_p = train_model(
            key, "VV_VH_DIFF", "bce_dice", augment=True, epochs=ARCH_EPOCHS[key], seed=42, tag=f"arch_{key}")
        calib = calibrate_threshold(val_t, val_p)
        th = calib["recommended_operating_threshold"]
        arch_results.append({
            "model": key, "val_iou_at_best_th": calib["max_iou"],
            "val_dice_at_best_th": calib["max_dice"],
            "best_threshold": th,
        })
        arch_models[key] = (m, tr, val_m, val_t, val_p, th, res)
        print(f"  {key:14s} valIoU={calib['max_iou']:.4f} valDice={calib['max_dice']:.4f} th={th:.2f}")

    best_arch = max(arch_results, key=lambda r: r["val_iou_at_best_th"])["model"]
    print(f"  -> selected architecture: {best_arch} (by validation IoU)")

    seg_model, seg_tr, seg_val_m, seg_val_t, seg_val_p, seg_th, seg_res = arch_models[best_arch]

    # =================================================================
    # CHANNEL / LOSS / AUGMENTATION ABLATIONS ON VALIDATION (on best arch)
    # =================================================================
    print("\n[3] Ablations on VALIDATION (channels, loss, augmentation) ...")
    ablation_rows = []

    channel_modes = ["VV", "VH", "VV_VH", "VV_VH_DIFF"]
    for ch in channel_modes:
        tag = {"VV": "ch_VV", "VH": "ch_VH", "VV_VH": "ch_VV_VH", "VV_VH_DIFF": "ch_DIFF"}[ch]
        m, tr, res, vm, vt, vp = train_model(best_arch, ch, "bce_dice", augment=True,
                                             epochs=ABLATION_EPOCHS, seed=42, tag=tag)
        calib = calibrate_threshold(vt, vp)
        best_pred = (vp >= calib["best_iou_threshold"]).astype(np.uint8)
        bm = compute_pixel_metrics(vt, best_pred, vp)
        ablation_rows.append({"ablation": "Input Channels", "variant": ch,
                              "iou": bm["iou"], "dice": bm["dice"],
                              "precision": bm["precision"], "recall": bm["recall"],
                              "fpr": bm["false_positive_rate"]})
        print(f"  channels {ch:10s} valIoU={bm['iou']:.4f} (th={calib['best_iou_threshold']})")

    for loss_name in ["bce", "dice", "bce_dice", "focal", "tversky", "focal_tversky"]:
        m, tr, res, vm, vt, vp = train_model(best_arch, "VV_VH_DIFF", loss_name, augment=True,
                                             epochs=ABLATION_EPOCHS, seed=42, tag=f"loss_{loss_name}")
        calib = calibrate_threshold(vt, vp)
        best_pred = (vp >= calib["best_iou_threshold"]).astype(np.uint8)
        bm = compute_pixel_metrics(vt, best_pred, vp)
        ablation_rows.append({"ablation": "Loss Formulation", "variant": loss_name.upper(),
                              "iou": bm["iou"], "dice": bm["dice"],
                              "precision": bm["precision"], "recall": bm["recall"],
                              "fpr": bm["false_positive_rate"]})
        print(f"  loss {loss_name:12s} valIoU={bm['iou']:.4f}")

    for aug_lab, aug_obj in [("No Augmentation", None), ("Physical SAR Augmentation", SARAugmentor())]:
        m, tr, res, vm, vt, vp = train_model(best_arch, "VV_VH_DIFF", "bce_dice", augment=aug_obj is not None,
                                             epochs=ABLATION_EPOCHS, seed=42, tag=f"aug_{'on' if aug_obj else 'off'}")
        calib = calibrate_threshold(vt, vp)
        best_pred = (vp >= calib["best_iou_threshold"]).astype(np.uint8)
        bm = compute_pixel_metrics(vt, best_pred, vp)
        ablation_rows.append({"ablation": "Augmentation", "variant": aug_lab,
                              "iou": bm["iou"], "dice": bm["dice"],
                              "precision": bm["precision"], "recall": bm["recall"],
                              "fpr": bm["false_positive_rate"]})
        print(f"  aug  {aug_lab:26s} valIoU={bm['iou']:.4f}")

    # Preprocessing experiment (percentile vs robust vs min_max)
    print("\n[4] Preprocessing experiment on VALIDATION ...")
    for strat in ["percentile", "robust", "min_max", "z_score"]:
        prep = SARPreprocessor(strategy=strat)
        m, tr, res, vm, vt, vp = train_model(best_arch, "VV_VH_DIFF", "bce_dice", augment=True,
                                             epochs=ABLATION_EPOCHS, seed=42, preprocessor=prep, tag=f"pp_{strat}")
        calib = calibrate_threshold(vt, vp)
        best_pred = (vp >= calib["best_iou_threshold"]).astype(np.uint8)
        bm = compute_pixel_metrics(vt, best_pred, vp)
        ablation_rows.append({"ablation": "Preprocessing", "variant": strat,
                              "iou": bm["iou"], "dice": bm["dice"],
                              "precision": bm["precision"], "recall": bm["recall"],
                              "fpr": bm["false_positive_rate"]})
        print(f"  preproc {strat:10s} valIoU={bm['iou']:.4f}")

    # =================================================================
    # HARD-NEGATIVE MINING (train+val only) + RETRAIN
    # =================================================================
    print("\n[5] Hard-negative mining from train+val (never test) ...")
    hn = extract_hard_negatives(seg_model, train + val, threshold=seg_th,
                                fp_pixel_threshold=50, preprocessor=PREP,
                                output_path="data/hard_negatives/hard_negatives_manifest.json")
    aug_train = build_hard_negative_augmented_train_set(train, hn, oversample_factor=3)
    print(f"  mined {len(hn)} hard negatives -> augmented train set = {len(aug_train)}")

    hn_model, hn_tr, hn_res, hn_val_m, hn_val_t, hn_val_p = train_model(
        best_arch, "VV_VH_DIFF", "bce_dice", augment=True, epochs=HN_EPOCHS, seed=42, tag=f"hn_{best_arch}",
        sample_set={"train": aug_train, "val": val})
    hn_calib = calibrate_threshold(hn_val_t, hn_val_p) if len(hn_val_t) else None
    print(f"  HN retrained val dice={hn_val_m['dice']:.4f} (before {seg_val_m['dice']:.4f})")

    # =================================================================
    # TWO-STAGE SYSTEM (on train crops, via seg pipeline)
    # =================================================================
    print("\n[6] Two-stage system: train stage-B look-alike classifier ...")
    crops, crop_labels, crop_log = prepare_stage_b_crops_for_training(
        seg_model, train, device=DEVICE, seg_threshold=seg_th, min_area=DEFAULT_MIN_AREA)
    classifier = build_model("classifier", in_channels=3, num_classes=3)
    train_stage_b_classifier(classifier, crops, crop_labels, device=DEVICE, epochs=12)
    print(f"  stage-B trained on {len(crop_labels)} crops")

    two_stage = TwoStageOilDetector(seg_model, classifier, seg_threshold=seg_th,
                                    classifier_threshold=0.50, device=DEVICE, preprocessor=PREP)

    # =================================================================
    # THRESHOLD + CALIBRATION ON VALIDATION (final model = base vs HN, by val)
    # =================================================================
    print("\n[7] Threshold + calibration on VALIDATION ...")
    # Decide final model by validation IoU between base and hard-negative retrain.
    base_calib = calibrate_threshold(seg_val_t, seg_val_p)
    hn_calib_m = calibrate_threshold(hn_val_t, hn_val_p) if len(hn_val_t) else base_calib
    if hn_calib_m["max_iou"] > base_calib["max_iou"]:
        final_model, final_th = hn_model, hn_calib_m["best_iou_threshold"]
        final_val_t, final_val_p = hn_val_t, hn_val_p
        print(f"  -> selected FINAL = HN retrained (valIoU {hn_calib_m['max_iou']:.4f} vs base {base_calib['max_iou']:.4f})")
    else:
        final_model, final_th = seg_model, base_calib["best_iou_threshold"]
        final_val_t, final_val_p = seg_val_t, seg_val_p
        print(f"  -> selected FINAL = base {best_arch} (valIoU {base_calib['max_iou']:.4f} vs HN {hn_calib_m['max_iou']:.4f})")

    calib_full = calibrate_threshold(final_val_t, final_val_p)
    ece_raw = compute_expected_calibration_error(final_val_t, final_val_p)
    brier_raw = compute_brier_score(final_val_t, final_val_p)
    temp = fit_temperature_scaling(final_val_t, final_val_p)
    cal_p = recalibrate_probabilities(final_val_p, temp)
    ece_cal = compute_expected_calibration_error(final_val_t, cal_p)
    brier_cal = compute_brier_score(final_val_t, cal_p)
    print(f"  ECE raw={ece_raw['ece_percentage']:.2f}% cal={ece_cal['ece_percentage']:.2f}% "
          f"(T={temp:.3f}) Brier {brier_raw:.4f}->{brier_cal:.4f}")

    calibration_report = {
        "threshold": final_th,
        "sweep": calib_full,
        "temperature": temp,
        "ece_raw": ece_raw["expected_calibration_error"],
        "ece_calibrated": ece_cal["expected_calibration_error"],
        "brier_raw": brier_raw,
        "brier_calibrated": brier_cal,
    }
    with open(REPORTS / "calibration.json", "w") as f:
        json.dump(calibration_report, f, indent=2, default=float)

    # =================================================================
    # FROZEN TEST EVALUATION (once)
    # =================================================================
    print("\n[8] FROZEN TEST evaluation (all decisions frozen now) ...")
    test_results = []
    test_images = [np.array(Image.open(s["image_path"])) for s in test]
    test_masks = [(np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8) for s in test]

    def frozen_eval(model_key_or_system, label):
        probs = []
        for img in test_images:
            p = infer_prob(model_key_or_system, img)
            probs.append(p)
        probs = np.stack(probs)
        pred_bin = (probs >= final_th).astype(np.uint8)
        px = compute_pixel_metrics(np.stack(test_masks), pred_bin, probs)
        obj = evaluate_object_detection(np.stack(test_masks), pred_bin)
        ece = compute_expected_calibration_error(np.stack(test_masks), probs)
        brier = compute_brier_score(np.stack(test_masks), probs)
        lat = measure_latency(model_key_or_system)
        test_results.append({"model": label, "iou": px["iou"], "dice": px["dice"],
                             "precision": px["precision"], "recall": px["recall"],
                             "pr_auc": px["pr_auc"], "fpr": px["false_positive_rate"],
                             "fnr": px["false_negative_rate"], "ece": ece["expected_calibration_error"],
                             "brier": brier, "obj_prec": obj["object_precision"],
                             "obj_rec": obj["object_recall"], "obj_f1": obj["object_f1"],
                             "latency_ms": lat})
        print(f"  {label:34s} IoU={px['iou']:.4f} Dice={px['dice']:.4f} Prec={px['precision']:.4f} "
              f"Rec={px['recall']:.4f} ECE={ece['expected_calibration_error']:.4f}")

    # classical baseline
    classical = build_model("classical")
    c_preds, c_probs = [], []
    for img in test_images:
        pbin, pconf = classical.predict(img)
        c_preds.append(pbin)
        c_probs.append(pconf)
    cpx = compute_pixel_metrics(np.stack(test_masks), np.stack(c_preds), np.stack(c_probs))
    cobj = evaluate_object_detection(np.stack(test_masks), np.stack(c_preds))
    test_results.append({"model": "Classical (Otsu)", "iou": cpx["iou"], "dice": cpx["dice"],
                         "precision": cpx["precision"], "recall": cpx["recall"],
                         "pr_auc": cpx["pr_auc"], "fpr": cpx["false_positive_rate"],
                         "fnr": cpx["false_negative_rate"],
                         "ece": cpx["pr_auc"] if False else compute_expected_calibration_error(np.stack(test_masks), np.stack(c_probs))["expected_calibration_error"],
                         "brier": compute_brier_score(np.stack(test_masks), np.stack(c_probs)),
                         "obj_prec": cobj["object_precision"], "obj_rec": cobj["object_recall"],
                         "obj_f1": cobj["object_f1"], "latency_ms": measure_latency_classical()})

    # deep models
    for key in ["unet", "unet_plus_plus"]:
        mmodel = arch_models[key][0]
        mmodel.to(DEVICE).eval()
        frozen_eval(mmodel, f"{key} (VV_VH_DIFF, bce_dice)")

    frozen_eval(seg_model, f"{best_arch} (base)")

    # hard-negative model for comparison
    hn_model.to(DEVICE).eval()
    frozen_eval(hn_model, f"{best_arch}+HN (hard-negative retrain)")

    # selected final model
    final_label = f"{best_arch} (FINAL selected)"
    frozen_eval(final_model, final_label)

    # two-stage
    ts_preds = []
    for img in test_images:
        rm, _, _ = two_stage.predict(img)
        ts_preds.append(rm.astype(np.uint8))
    ts_px = compute_pixel_metrics(np.stack(test_masks), np.stack(ts_preds))
    ts_obj = evaluate_object_detection(np.stack(test_masks), np.stack(ts_preds))
    test_results.append({"model": "Two-Stage (SegFormer + Lookalike Clf)", "iou": ts_px["iou"],
                         "dice": ts_px["dice"], "precision": ts_px["precision"], "recall": ts_px["recall"],
                         "pr_auc": ts_px["pr_auc"], "fpr": ts_px["false_positive_rate"],
                         "fnr": ts_px["false_negative_rate"],
                         "ece": compute_expected_calibration_error(np.stack(test_masks), np.stack(ts_preds).astype(np.float32))["expected_calibration_error"],
                         "brier": compute_brier_score(np.stack(test_masks), np.stack(ts_preds).astype(np.float32)),
                         "obj_prec": ts_obj["object_precision"], "obj_rec": ts_obj["object_recall"],
                         "obj_f1": ts_obj["object_f1"], "latency_ms": measure_two_stage_latency(two_stage)})

    # =================================================================
    # MULTI-SEED STABILITY (final architecture)
    # =================================================================
    # Memory relief: after the frozen test only final_model/final_th and the
    # test arrays are needed. Drop the retained training-stage models and val
    # probability arrays (their metrics are already frozen in the reports).
    # Without this, ~15 resident torch models push commit high enough that the
    # OS pagefile balloons and the process can be silently OOM-terminated.
    import gc as _gc
    for _n in ["arch_models", "seg_model", "seg_tr", "seg_res", "seg_val_t", "seg_val_p",
               "hn_model", "hn_tr", "hn_res", "hn_val_t", "hn_val_p",
               "classifier", "two_stage", "classical",
               "c_preds", "c_probs", "ts_preds"]:
        if _n in globals():
            del globals()[_n]
    _gc.collect()

    print("\n[9] Multi-seed stability (3 seeds) ...")
    seeds = [42, 123, 999]
    seed_res = []
    for sd in seeds:
        m, tr, res, vm, vt, vp = train_model(best_arch, "VV_VH_DIFF", "bce_dice", augment=True,
                                             epochs=MULTISEED_EPOCHS, seed=sd, tag=f"seed_{sd}")
        calib = calibrate_threshold(vt, vp)
        bestp = (vp >= calib["best_iou_threshold"]).astype(np.uint8)
        bm = compute_pixel_metrics(vt, bestp, vp)
        seed_res.append({"seed": sd, "val_iou": bm["iou"], "val_dice": bm["dice"]})
        print(f"  seed {sd}: valIoU={bm['iou']:.4f} valDice={bm['dice']:.4f}")

    # =================================================================
    # ROBUSTNESS + CROSS-DATASET on final model
    # =================================================================
    print("\n[10] Robustness + cross-dataset generalization ...")
    def eval_perturbed_batch(p_imgs, g_masks):
        preds = []
        for im in p_imgs:
            p = infer_prob(final_model, im)
            preds.append((p >= final_th).astype(np.uint8))
        return compute_pixel_metrics(np.stack(g_masks), np.stack(preds))

    robustness_results = run_robustness_benchmark(eval_perturbed_batch, test_images, test_masks)

    # cross-dataset: evaluate final model trained on A against B
    ext_inv = scan_dataset(EXTERNAL_ROOT)
    ext_samples = ext_inv["samples"]
    ext_px, ext_obj, ext_ece, ext_brier, _, _ = eval_on_split(final_model, ext_samples)
    print(f"  cross-dataset external: IoU={ext_px['iou']:.4f} Dice={ext_px['dice']:.4f}")
    cross_dataset_rows = [
        {"evaluation_domain": "In-Domain Test", "dataset_name": "Dataset A (Arabian Sea)",
         "iou": next(r["iou"] for r in test_results if r["model"] == final_label),
         "dice": next(r["dice"] for r in test_results if r["model"] == final_label),
         "precision": next(r["precision"] for r in test_results if r["model"] == final_label),
         "recall": next(r["recall"] for r in test_results if r["model"] == final_label),
         "fpr": next(r["fpr"] for r in test_results if r["model"] == final_label)},
        {"evaluation_domain": "Cross-Dataset External", "dataset_name": "Dataset B (Singapore Strait)",
         "iou": ext_px["iou"], "dice": ext_px["dice"], "precision": ext_px["precision"],
         "recall": ext_px["recall"], "fpr": ext_px["false_positive_rate"]},
    ]

    # =================================================================
    # EXPORT ALL REPORTS
    # =================================================================
    print("\n[11] Exporting reports ...")

    def write_csv(name, fieldnames, rows):
        with open(REPORTS / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

    write_csv("final_test_results.csv",
              ["model", "iou", "dice", "precision", "recall", "pr_auc", "fpr", "fnr",
               "ece", "brier", "obj_prec", "obj_rec", "obj_f1", "latency_ms"],
              [dict((k, r[k]) for k in ["model", "iou", "dice", "precision", "recall", "pr_auc",
                                        "fpr", "fnr", "ece", "brier", "obj_prec", "obj_rec", "obj_f1", "latency_ms"])
               for r in test_results])
    write_csv("model_comparison.csv", list(test_results[0].keys()), test_results)
    write_csv("ablation_results.csv", ["ablation", "variant", "iou", "dice", "precision", "recall", "fpr"], ablation_rows)
    write_csv("robustness_results.csv", ["condition", "iou", "dice", "precision", "recall", "fpr"], robustness_results)
    write_csv("cross_dataset_results.csv", ["evaluation_domain", "dataset_name", "iou", "dice", "precision", "recall", "fpr"], cross_dataset_rows)
    write_csv("model_selection.csv", ["model", "val_iou_at_best_th", "val_dice_at_best_th", "best_threshold"], arch_results)
    write_csv("multi_seed.csv", ["seed", "val_iou", "val_dice"], seed_res)

    summary = {
        "device": str(DEVICE),
        "selected_architecture": best_arch,
        "selected_threshold": final_th,
        "leakage": leak["verification_status"],
        "hard_negatives_mined": len(hn),
        "hard_negative_train_set": len(aug_train),
        "temperature": temp,
        "calibration": {
            "ece_raw": ece_raw["expected_calibration_error"],
            "ece_calibrated": ece_cal["expected_calibration_error"],
        },
        "test_results": [
            {k: (r[k] if k != "latency_ms" else (float(r[k]) if not np.isnan(r[k]) else None))
             if isinstance(r.get(k), float) else r[k] for k in ["model", "iou", "dice"]}
            for r in test_results[:3]
        ],
    }
    with open(REPORTS / "campaign_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Freeze the FINAL model artifact for production services.
    BEST_DIR = Path("models/best_model")
    BEST_DIR.mkdir(exist_ok=True)
    best_ckpt_name = "arch_unet_best.pt" if best_arch == "unet" else f"arch_{best_arch}_best.pt"
    best_ckpt = torch.load(CHKPT_DIR / best_ckpt_name, map_location="cpu")
    best_ckpt["metadata"] = dict(best_ckpt.get("metadata", {}),
                                 production=True,
                                 frozen_threshold=float(final_th),
                                 frozen_test={"iou": float(next(r["iou"] for r in test_results
                                                                 if r["model"] == final_label)),
                                              "dice": float(next(r["dice"] for r in test_results
                                                                 if r["model"] == final_label))},
                                 calibration={"temperature": float(temp),
                                              "ece_calibrated": float(ece_cal["expected_calibration_error"])})
    torch.save(best_ckpt, BEST_DIR / "marinex_unet_v1.pt")
    print(f"  -> frozen FINAL model -> {BEST_DIR / 'marinex_unet_v1.pt'} (th={final_th:.3f})")

    print("\n[OK] Campaign complete. Reports written to reports/.")
    return 0


def measure_two_stage_latency(system, n=4):
    import time
    img = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    with torch.no_grad():
        for _ in range(2):
            system.predict(img)
        t0 = time.time()
        for _ in range(n):
            system.predict(img)
    return (time.time() - t0) / n * 1000.0


def measure_latency_classical():
    import time
    cls = build_model("classical")
    x = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    t0 = time.time()
    for _ in range(8):
        cls.predict(x)
    return (time.time() - t0) / 8 * 1000.0


if __name__ == "__main__":
    raise SystemExit(main())