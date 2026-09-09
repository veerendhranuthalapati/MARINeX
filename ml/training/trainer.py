"""
PyTorch Training Engine for SAR Oil Spill Segmentation Models.
Implements early stopping, best checkpointing, validation metrics tracking, and MLflow logging.
"""

import os
import time
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np
from typing import Dict, Any, Optional
from ml.models.base import BaseSegmentationModel
from ml.evaluation.metrics import compute_pixel_metrics

try:
    import mlflow
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

class SegmentationTrainer:
    def __init__(
        self,
        model: BaseSegmentationModel,
        loss_fn: nn.Module,
        optimizer: torch.optim.Optimizer,
        lr_scheduler: Optional[Any] = None,
        device: Optional[torch.device] = None,
        experiment_name: str = "oil_spill_segmentation",
        checkpoint_dir: str = "models/checkpoints",
    ):
        self.model = model
        self.loss_fn = loss_fn
        self.optimizer = optimizer
        self.lr_scheduler = lr_scheduler
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        self.experiment_name = experiment_name
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

        self.best_val_dice = -1.0
        self.best_checkpoint_path = ""
        self.history = []

    def train_epoch(self, train_loader: DataLoader) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        all_targets = []
        all_preds = []

        for images, masks, _ in train_loader:
            images = images.to(self.device)
            masks = masks.to(self.device)

            self.optimizer.zero_grad()
            logits = self.model(images)
            loss = self.loss_fn(logits, masks)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item() * images.size(0)

            probs = torch.sigmoid(logits.squeeze(1)).detach().cpu().numpy()
            targets_np = masks.detach().cpu().numpy()
            all_preds.append((probs >= 0.5).astype(np.uint8))
            all_targets.append(targets_np.astype(np.uint8))

        all_preds = np.concatenate(all_preds, axis=0)
        all_targets = np.concatenate(all_targets, axis=0)
        metrics = compute_pixel_metrics(all_targets, all_preds)
        metrics["loss"] = total_loss / len(train_loader.dataset)
        return metrics

    def validate(self, val_loader: DataLoader, threshold: float = 0.5) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        all_targets = []
        all_preds = []
        all_probs = []

        with torch.no_grad():
            for images, masks, _ in val_loader:
                images = images.to(self.device)
                masks = masks.to(self.device)

                logits = self.model(images)
                loss = self.loss_fn(logits, masks)
                total_loss += loss.item() * images.size(0)

                probs = torch.sigmoid(logits.squeeze(1)).cpu().numpy()
                targets_np = masks.cpu().numpy()

                all_probs.append(probs)
                all_preds.append((probs >= threshold).astype(np.uint8))
                all_targets.append(targets_np.astype(np.uint8))

        all_probs = np.concatenate(all_probs, axis=0)
        all_preds = np.concatenate(all_preds, axis=0)
        all_targets = np.concatenate(all_targets, axis=0)

        metrics = compute_pixel_metrics(all_targets, all_preds, all_probs)
        metrics["loss"] = total_loss / len(val_loader.dataset)
        return metrics, all_targets, all_probs

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 15,
        early_stopping_patience: int = 5,
        save_prefix: str = "model",
    ) -> Dict[str, Any]:
        patience_counter = 0
        start_time = time.time()

        for epoch in range(1, epochs + 1):
            t_train = self.train_epoch(train_loader)
            val_metrics, _, _ = self.validate(val_loader)

            if self.lr_scheduler:
                self.lr_scheduler.step()

            # Record history
            epoch_log = {
                "epoch": epoch,
                "train_loss": t_train["loss"],
                "train_dice": t_train["dice"],
                "train_iou": t_train["iou"],
                "val_loss": val_metrics["loss"],
                "val_dice": val_metrics["dice"],
                "val_iou": val_metrics["iou"],
                "val_precision": val_metrics["precision"],
                "val_recall": val_metrics["recall"],
            }
            self.history.append(epoch_log)

            print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {t_train['loss']:.4f} Dice: {t_train['dice']:.4f} | Val Loss: {val_metrics['loss']:.4f} Dice: {val_metrics['dice']:.4f} IoU: {val_metrics['iou']:.4f}")

            # Checkpoint best model
            if val_metrics["dice"] > self.best_val_dice:
                self.best_val_dice = val_metrics["dice"]
                self.best_checkpoint_path = os.path.join(self.checkpoint_dir, f"{save_prefix}_best.pt")
                self.model.save_weights(self.best_checkpoint_path, extra_meta={
                    "epoch": epoch,
                    "val_dice": val_metrics["dice"],
                    "val_iou": val_metrics["iou"],
                    "val_precision": val_metrics["precision"],
                    "val_recall": val_metrics["recall"]
                })
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    print(f"Early stopping triggered at epoch {epoch}.")
                    break

        duration = time.time() - start_time
        return {
            "best_val_dice": self.best_val_dice,
            "best_checkpoint": self.best_checkpoint_path,
            "training_duration_sec": duration,
            "epochs_trained": len(self.history),
            "history": self.history
        }
