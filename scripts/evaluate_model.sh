#!/usr/bin/env bash
# Phase 41: Evaluate a trained model artifact with provenance metadata.
# Usage: ./scripts/evaluate_model.sh [checkpoint.pt] [threshold]
set -euo pipefail

ARTIFACT="${1:-models/best_model/marinex_unet_v1.pt}"
THRESHOLD="${2:-0.70}"

[ -f "$ARTIFACT" ] || { echo "model artifact not found: $ARTIFACT"; exit 1; }

echo "[evaluate] artifact=$ARTIFACT threshold=$THRESHOLD"
python - <<PY
import sys
sys.path.insert(0, ".")
import json
from ml.models.registry import build_model
from ml.data_audit.split_dataset import create_group_aware_split

# Evaluated with the shared benchmark harness when available.
try:
    from ml.evaluation.benchmark import evaluate_checkpoint_once
    res = evaluate_checkpoint_once("$ARTIFACT", threshold=float("$THRESHOLD"))
    print(json.dumps(res, indent=2, default=str))
except ImportError:
    print("ml.evaluation.benchmark not present; run 'python ml/evaluate.py --config ...'")
PY