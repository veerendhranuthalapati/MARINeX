"""
Config-Driven Training Entrypoint (Phase 14, 29).

Usage:
    python ml/train.py --config configs/training/segformer.yaml

Configuration is environment-independent. Paths resolve through env vars
(DATA_ROOT, ARTIFACT_ROOT, MLFLOW_URI); no local paths are hard-coded.

Flow:
    load split manifest -> scan dataset -> build loaders
    -> train (reproducible seed) -> validate -> calibrate threshold (val only)
    -> evaluate held-out test ONCE -> save artifact + provenance metadata
    -> optional MLflow logging
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import torch
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.data.dataset import Sentinel1SARSpillDataset, sar_collate_fn
from ml.data.transforms import SARAugmentor
from ml.data_audit.dataset_inventory import scan_dataset
from ml.models.registry import build_model
from ml.losses.segmentation_losses import get_loss_function
from ml.training.trainer import SegmentationTrainer
from ml.evaluation.metrics import compute_pixel_metrics
from ml.evaluation.calibration import calibrate_threshold, compute_expected_calibration_error

try:
    import mlflow
except ImportError:
    mlflow = None


def resolve_paths(conf: dict) -> dict:
    """Resolve DATA_ROOT / ARTIFACT_ROOT / split path from env or config."""
    env = os.environ.get("DATA_ROOT") or conf.get("data_root")
    artifact = os.environ.get("ARTIFACT_ROOT") or conf.get("artifact_root") or "models"
    split = conf.get("split_path") or "data/splits/split_group_aware_v1.json"
    dataset_uri = conf.get("dataset_uri") or conf.get("dataset", {}).get("dataset_root")
    return {
        "data_root": env,
        "artifact_root": artifact,
        "split_path": split,
        "dataset_uri": dataset_uri,
    }


def load_samples(data_root: str | None, dataset_uri: str | None) -> tuple[dict, list]:
    base = Path(data_root or ".")
    if dataset_uri:
        dataset_dir = Path(dataset_uri)
        if not dataset_dir.is_absolute():
            dataset_dir = base / dataset_dir
    else:
        dataset_dir = base / "data/datasets/sentinel1_primary"
    inventory = scan_dataset(str(dataset_dir))
    return inventory, inventory["samples"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/training/segformer.yaml")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)

    model_cfg = conf["model"]
    data_cfg = conf["data"]
    train_cfg = conf["training"]
    seed = args.seed if args.seed is not None else train_cfg.get("seed", 42)
    epochs = args.epochs if args.epochs is not None else train_cfg.get("epochs", 12)

    torch.manual_seed(seed)
    np.random.seed(seed)

    resolved = resolve_paths(conf)
    split_path = Path(resolved["split_path"])
    if not split_path.is_absolute():
        split_path = Path(".") / split_path

    with open(split_path, "r", encoding="utf-8") as f:
        split_manifest = json.load(f)

    inventory, samples = load_samples(resolved["data_root"], resolved["dataset_uri"])
    sample_map = {s["sample_id"]: s for s in samples}

    def sel(key: str) -> list:
        return [sample_map[sid] for sid in split_manifest["splits"][key]]

    train_samples, val_samples, test_samples = sel("train"), sel("val"), sel("test")
    print(f"[train] {model_cfg['name']} | train={len(train_samples)} val={len(val_samples)} test={len(test_samples)} seed={seed}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    channels = data_cfg.get("channels", "VV_VH_DIFF")

    use_aug = train_cfg.get("augmentation", True)
    augmentor = SARAugmentor() if use_aug else None
    ds_train = Sentinel1SARSpillDataset(train_samples, channels=channels, is_training=True, augmentor=augmentor)
    ds_val = Sentinel1SARSpillDataset(val_samples, channels=channels, is_training=False)
    ds_test = Sentinel1SARSpillDataset(test_samples, channels=channels, is_training=False)

    bs = data_cfg.get("batch_size", 8)
    train_loader = torch.utils.data.DataLoader(ds_train, batch_size=bs, shuffle=True, collate_fn=sar_collate_fn)
    val_loader = torch.utils.data.DataLoader(ds_val, batch_size=bs, shuffle=False, collate_fn=sar_collate_fn)
    test_loader = torch.utils.data.DataLoader(ds_test, batch_size=len(test_samples), shuffle=False, collate_fn=sar_collate_fn)

    model = build_model(model_cfg["name"], in_channels=model_cfg.get("in_channels", 3), num_classes=model_cfg.get("num_classes", 1))
    opt_cfg = train_cfg.get("optimizer", "adamw")
    lr = train_cfg.get("learning_rate", 8e-4)
    wd = train_cfg.get("weight_decay", 1e-4)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    loss_fn = get_loss_function(train_cfg.get("loss", "bce_dice"))

    artifact_root = Path(resolved["artifact_root"])
    checkpoint_dir = artifact_root / "checkpoints"
    trainer = SegmentationTrainer(
        model, loss_fn, optimizer, device=device,
        experiment_name=f"{model_cfg['name']}_{seed}",
        checkpoint_dir=str(checkpoint_dir),
    )

    fit_result = trainer.fit(
        train_loader, val_loader,
        epochs=epochs,
        early_stopping_patience=train_cfg.get("early_stopping_patience", 5),
        save_prefix=model_cfg["name"],
    )

    # Threshold calibration on VALIDATION set only.
    val_metrics, val_targets, val_probs = trainer.validate(val_loader)
    calib = calibrate_threshold(val_targets, val_probs)
    th = calib["recommended_operating_threshold"]
    ece = compute_expected_calibration_error(val_targets, val_probs)

    # Held-out test evaluation (single pass).
    test_metrics, test_targets, test_probs = trainer.validate(test_loader, threshold=th)

    artifact_path = artifact_root / "best_model" / f"marinex_{model_cfg['name']}_v1.pt"
    model.save_weights(str(artifact_path), extra_meta={
        "model_name": f"marinex-{model_cfg['name']}-v1.0.0",
        "optimal_threshold": float(th),
        "input_channels": ["VV", "VH", "VV_minus_VH"],
        "normalization": data_cfg.get("normalization", "percentile_2_98"),
        "seed": seed,
        "test_metrics": test_metrics,
        "val_metrics": val_metrics,
        "ece": ece["expected_calibration_error"],
        "config": conf,
        "git_commit": os.popen("git rev-parse HEAD 2>/dev/null").read().strip() if os.path.exists(".git") else "unknown",
    })

    result = {
        "model": model_cfg["name"],
        "seed": seed,
        "epochs": epochs,
        "threshold": th,
        "ece": ece["expected_calibration_error"],
        "val": val_metrics,
        "test": test_metrics,
        "fit": {k: fit_result[k] for k in ("best_val_dice", "training_duration_sec", "epochs_trained")},
        "artifact": str(artifact_path),
    }

    out_path = Path("reports") / f"train_result_{model_cfg['name']}_seed{seed}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=float)

    print(json.dumps(result, indent=2, default=float))

    if mlflow is not None and os.environ.get("MLFLOW_URI"):
        mlflow.set_tracking_uri(os.environ["MLFLOW_URI"])
        with mlflow.start_run(run_name=f"{model_cfg['name']}_seed{seed}"):
            for k, v in conf.items():
                mlflow.log_params({f"config/{k}": json.dumps(v, default=str)})
            mlflow.log_metrics({f"test/{k}": float(v) for k, v in test_metrics.items() if isinstance(v, (int, float))})
            mlflow.log_metrics({"test/optimal_threshold": float(th), "test/ece": float(ece["expected_calibration_error"])})
            mlflow.log_artifact(str(artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())