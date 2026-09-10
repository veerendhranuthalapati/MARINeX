"""
Dataset Manifest System for MARINeX.

Every dataset (SAR, AIS, environment) has a declarative manifest that describes
what data EXISTS -- without requiring the data itself to be downloaded.

Manifests answer:
  * What is available?
  * Where does it live (local path, remote URI, object store)?
  * How big is it, what are its channels/resolution/coverage/labels?
  * What split and checksum descriptor apply?

Design rules:
  * Querying the catalog NEVER triggers a download.
  * Local availability is derived by scanning local_path if present.
  * Remote datasets carry remote_uri + provider and report status "remote".
"""

from __future__ import annotations

import os
import json
import hashlib
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DatasetManifest:
    dataset_id: str
    dataset_name: str
    source: str
    license: str
    version: str
    provider: str            # "local" | "remote" | "object-storage"
    local_path: Optional[str] = None
    remote_uri: Optional[str] = None
    channels: List[str] = field(default_factory=list)
    resolution_m: Optional[float] = None
    resolution_px: Optional[int] = None
    geographic_coverage: str = ""
    temporal_coverage: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    split_path: Optional[str] = None
    n_samples: Optional[int] = None
    n_files: Optional[int] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    status: str = "unknown"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DatasetManifest":
        known = {f for f in DatasetManifest.__dataclass_fields__}
        return DatasetManifest(**{k: v for k, v in d.items() if k in known})


def load_dataset_config(path: str | Path) -> Dict[str, Any]:
    """Load a dataset descriptor (YAML or JSON)."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        return json.load(f)


def _dir_size_bytes(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def _file_count(root: Path) -> int:
    return sum(1 for p in root.rglob("*") if p.is_file())


def _root_checksum(root: Path) -> Optional[str]:
    """Checksum over sorted relative paths + sizes (content-agnostic but cheap)."""
    try:
        h = hashlib.sha256()
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                h.update(rel.encode("utf-8"))
                h.update(str(p.stat().st_size).encode("utf-8"))
        return h.hexdigest()
    except Exception:
        return None


def build_manifest(
    config: Dict[str, Any],
    data_root: str | Path = "data",
) -> DatasetManifest:
    """Build a manifest from a dataset descriptor, resolving local availability."""
    m = DatasetManifest.from_dict(config)

    if m.local_path:
        lp = Path(m.local_path)
        local = lp if lp.is_absolute() else Path(data_root).parent / lp
    else:
        local = None

    if local is not None and local.exists():
        if m.n_samples is None:
            # Best-effort sample count: paired image/mask discovery is dataset-specific,
            # so we only report files + bytes here; the SAR audit computes real counts.
            pass
        m.n_files = _file_count(local)
        m.size_bytes = _dir_size_bytes(local)
        m.checksum = _root_checksum(local)
        m.status = "local"
    elif m.remote_uri:
        m.status = "remote"
    else:
        m.status = "missing"

    return m


def save_manifest(manifest: DatasetManifest, out_dir: str | Path = "data/manifests") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{manifest.dataset_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2)
    return out_path


def catalog(
    configs_glob: str = "configs/datasets/*.yaml",
    out_dir: str = "data/manifests",
) -> List[Dict[str, Any]]:
    """Load all dataset descriptors and resolve status/size for each.

    Never downloads anything. Safe to call at startup / in the dataset page.
    """
    from pathlib import Path as P
    manifests: List[Dict[str, Any]] = []
    for cfg in sorted(P(".").glob(configs_glob)):
        if not cfg.exists():
            continue
        config = load_dataset_config(cfg)
        m = build_manifest(config)
        save_manifest(m, out_dir)
        manifests.append(m.to_dict())
    return manifests


def catalog_summary(manifests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Human + machine readable summary of the catalog."""
    return {
        "datasets": manifests,
        "counts": {
            "total": len(manifests),
            "local": sum(1 for m in manifests if m["status"] == "local"),
            "remote": sum(1 for m in manifests if m["status"] == "remote"),
            "missing": sum(1 for m in manifests if m["status"] == "missing"),
        },
    }


if __name__ == "__main__":
    import sys
    summary = catalog_summary(catalog())
    print(json.dumps(summary["counts"], indent=2))
    for m in summary["datasets"]:
        print(f"  {m['dataset_id']:40s} {m['status']:8s} {m.get('size_bytes') or '-'} bytes")