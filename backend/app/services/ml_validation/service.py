"""ML validation bundle service (Phase 47-48 frontend data source).

Serves the frozen, validated ML evaluation artifacts from reports/ and
models/production/ so the Model Intelligence and Explainability pages render
REAL numbers produced by the campaign - never fabricated for the UI.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
MODEL_ROOT = ROOT / "models" / "production"
REPORTS = ROOT / "reports"


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_csv(path: Path) -> Optional[List[Dict[str, Any]]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return None


class MLValidationService:

    @staticmethod
    def card() -> Dict[str, Any]:
        meta = _load_json(MODEL_ROOT / "metadata.json") or {}
        return {
            "production_model": meta,
            "model_comparison": _load_csv(REPORTS / "model_comparison.csv"),
            "final_test_results": _load_csv(REPORTS / "final_test_results.csv"),
            "multi_seed": _load_csv(REPORTS / "multi_seed.csv"),
            "ablation": _load_csv(REPORTS / "ablation_results.csv"),
            "calibration": _load_json(REPORTS / "calibration.json"),
            "cross_dataset": _load_json(REPORTS / "cross_dataset_results.csv") or _load_csv(REPORTS / "cross_dataset_results.csv"),
        }

    @staticmethod
    def validation() -> Dict[str, Any]:
        return {
            "robustness": _load_json(REPORTS / "robustness_results.csv") or _load_csv(REPORTS / "robustness_results.csv"),
            "scene_level": _load_csv(REPORTS / "scene_level_results.csv"),
            "slick_size": _load_csv(REPORTS / "slick_size_results.csv"),
            "lookalike": _load_csv(REPORTS / "lookalike_results.csv"),
            "error_taxonomy": _load_csv(REPORTS / "error_taxonomy.csv"),
            "slick_geometry": _load_csv(REPORTS / "slick_geometry_results.csv"),
            "drift_sanity": _load_json(REPORTS / "drift_sanity_results.json"),
            "drift_sensitivity": _load_csv(REPORTS / "drift_sensitivity.csv"),
            "ais_quality": _load_csv(REPORTS / "ais_quality_audit.csv"),
            "ais_trajectory": _load_json(REPORTS / "ais_trajectory_validation.json"),
            "calibration_detailed": _load_json(REPORTS / "calibration_detailed.json"),
            "reliability_curve": _load_csv(REPORTS / "reliability_curve.csv"),
            "confidence_histogram": _load_csv(REPORTS / "confidence_histogram.csv"),
            "dataset_audit": _load_json(REPORTS / "dataset_audit.json"),
        }

    @staticmethod
    def explainability() -> Dict[str, Any]:
        sanity = _load_json(REPORTS / "explainability" / "sanity.json") or {}
        exps = []
        exp_dir = REPORTS / "explainability"
        if exp_dir.exists():
            for f in sorted(exp_dir.glob("EXP-*.json")):
                data = _load_json(f)
                if data:
                    data["report_path"] = f.name
                    exps.append(data)
        return {"sanity": sanity, "examples": exps}


ml_service = MLValidationService()