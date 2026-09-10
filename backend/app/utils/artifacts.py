"""
Persists raw and post-processed ML outputs to disk for auditable evidence.

Phase 3/5: "Preserve both RAW MODEL OUTPUT and POSTPROCESSED OUTPUT."
We always write the raw soft-probability array and both masks next to each
other so the evidence ledger can reference exact artifacts.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
from app.core.config import settings


class DetectionArtifactStore:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or (settings.DATA_DIR / "processed" / "detections")

    def ensure_dir(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def save(
        self,
        scene_id: str,
        probs: np.ndarray,
        raw_mask: np.ndarray,
        post_mask: np.ndarray,
        meta: Dict[str, Any],
    ) -> str:
        run_id = f"{scene_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.ensure_dir()
        npz_path = self.root / f"{run_id}.npz"
        json_path = self.root / f"{run_id}.json"

        np.savez_compressed(
            npz_path,
            probs=probs.astype(np.float32),
            raw_mask=raw_mask.astype(np.uint8),
            post_mask=post_mask.astype(np.uint8),
        )
        import json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"run_id": run_id, "scene_id": scene_id, "meta": meta}, f,
                      indent=2, default=str)

        return str(npz_path)