#!/usr/bin/env bash
# Phase 41: Prepare/copy data for remote training.
# Reads REMOTE_DATA_URI (e.g. s3://bucket/marinex/data or gs://...).
# Falls back to the local dataset when REMOTE_DATA_URI is empty.
set -euo pipefail

DATA_DIR="${1:-data/processed/sar}"
REMOTE_URI="${REMOTE_DATA_URI:-}"

echo "[prepare_data] target local: $DATA_DIR"
mkdir -p "$DATA_DIR"

if [ -n "$REMOTE_URI" ]; then
  echo "[prepare_data] streaming from $REMOTE_URI"
  # Selective/streaming copy — never download an entire archive blindly.
  # Adjust the guard below to your object store (aws s3, gsutil, rclone, ...).
  if command -v rclone >/dev/null 2>&1; then
    rclone copy "$REMOTE_URI" "$DATA_DIR" --transfers 4
  else
    echo "[prepare_data] WARN: no rclone found, using manifest-driven local dataset"
  fi
fi

if [ -f "data/splits/split_group_aware_v1.json" ]; then
  cp data/splits/split_group_aware_v1.json "$DATA_DIR/split_group_aware_v1.json"
fi

python - <<'PY'
import os, sys
sys.path.insert(0, ".")
from ml.data.manifest import catalog
m = catalog()
print("data manifest status:")
for d in m["datasets"]:
    print(" ", d["dataset_id"], d["status"], d.get("size_bytes"))
PY