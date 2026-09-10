"""Tests for the dataset manifest system (ml/data/manifest.py)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.data.manifest import catalog, catalog_summary, load_dataset_config


def test_catalog_loads_without_download():
    manifests = catalog()
    ids = [m["dataset_id"] for m in manifests]
    assert "sentinel1-oilspill-primary-v1" in ids
    assert "sentinel1-oilspill-external-v1" in ids


def test_local_status_resolved():
    manifests = {m["dataset_id"]: m for m in catalog()}
    p = manifests["sentinel1-oilspill-primary-v1"]
    assert p["status"] == "local"
    assert p["n_samples"] == 120
    assert p["size_bytes"] > 0
    assert p["checksum"]


def test_summary_counts():
    s = catalog_summary(catalog())
    assert s["counts"]["total"] >= 2
    assert s["counts"]["local"] >= 2


def test_descriptor_fields_present():
    cfg = load_dataset_config("configs/datasets/sentinel1_oilspill_primary.yaml")
    for field in ("dataset_id", "dataset_name", "source", "license", "version",
                  "channels", "resolution_m", "labels", "split_path"):
        assert field in cfg, f"missing manifest field: {field}"