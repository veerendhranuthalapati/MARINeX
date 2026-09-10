#!/usr/bin/env bash
# Phase 41: Remote/cloud GPU setup (environment-independent, provider-agnostic).
set -euo pipefail

echo "[setup_gpu] Installing python deps for remote training"
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r backend/requirements.txt
pip install duckdb pyarrow pyyaml mlflow

echo "[setup_gpu] verifying torch + cuda"
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
PY