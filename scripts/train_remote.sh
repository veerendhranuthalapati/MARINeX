#!/usr/bin/env bash
# Phase 41: Remote training runner (provider-agnostic via env vars).
# Usage: ./scripts/train_remote.sh [config] [epochs] [seed]
set -euo pipefail

CONFIG="${1:-configs/training/unet_plus_plus.yaml}"
EPOCHS="${2:-}"
SEED="${3:-}"

echo "[train_remote] config=$CONFIG DATA_ROOT=${DATA_ROOT:-data} ARTIFACT_ROOT=${ARTIFACT_ROOT:-models} MLFLOW_URI=${MLFLOW_URI:-}"

EXTRA=()
[ -n "$EPOCHS" ] && EXTRA+=(--epochs "$EPOCHS")
[ -n "$SEED" ]   && EXTRA+=(--seed "$SEED")

python ml/train.py --config "$CONFIG" "${EXTRA[@]}"

# Optionally push artifact to object storage if REMOTE_ARTIFACT_URI set.
if [ -n "${REMOTE_ARTIFACT_URI:-}" ] && command -v rclone >/dev/null 2>&1; then
  echo "[train_remote] uploading artifacts to $REMOTE_ARTIFACT_URI"
  rclone copy models/best_model "$REMOTE_ARTIFACT_URI/best_model" --transfers 4
fi