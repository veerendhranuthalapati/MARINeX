"""
Data Quality Summary Service (Phase 31).

Computes a transparent, per-source data-quality assessment for an incident from
the ACTUAL pipeline inputs that contributed to the report - never fabricated:

  * satellite        - detection run outcome / ML confidence vs production minimum
  * environmental    - EnvironmentQualityReport (PASS / WARN / FAIL) for the window
  * drift            - whether a physics simulation actually produced output
  * ais              - number of vessel tracks actually scanned in the window
  * model            - production-model calibration expectation vs slick confidence

Overall quality is the worst of the contributing sources (strict pessimism), and
every grade carries an evidence-backed reason string. Nothing here can be
'PASS' unless real data was consumed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.status import DataQuality


class DataQualityService:
    ORDER = {DataQuality.PASS: 0, DataQuality.WARN: 1, DataQuality.FAIL: 2}

    @classmethod
    def _worst(cls, grades: list[DataQuality]) -> DataQuality:
        worst = DataQuality.PASS
        for g in grades:
            if cls.ORDER[g] > cls.ORDER[worst]:
                worst = g
        return worst

    @classmethod
    def assess(
        cls,
        *,
        detection_status: Optional[str] = None,
        detection_confidence: Optional[float] = None,
        env_quality: Optional[Dict[str, Any]] = None,
        drift_ok: Optional[bool] = None,
        ais_track_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        checks: list[Dict[str, Any]] = []
        grades: list[DataQuality] = []

        # --- Satellite / detection source ---
        if detection_status == "SLICKS_FOUND":
            sat_grade = DataQuality.PASS
            detail = "Production satellite detection produced slicks above operational confidence."
        elif detection_status == "LOW_CONFIDENCE":
            sat_grade = DataQuality.WARN
            detail = "Satellite detection ran but confidence was below operational threshold; flagged for analyst review."
        elif detection_status == "NO_SLICKS":
            sat_grade = DataQuality.WARN
            detail = "Satellite detection completed but no slicks were identified in the scene."
        elif detection_status == "ERROR":
            sat_grade = DataQuality.FAIL
            detail = "Satellite detection pipeline errored; no detection output available."
        else:
            sat_grade = DataQuality.FAIL
            detail = "No satellite detection run recorded for this incident."
        checks.append({"source": "satellite", "grade": sat_grade.value, "detail": detail})
        grades.append(sat_grade)

        # --- ML model confidence vs production minimum ---
        if detection_confidence is None:
            ml_grade = DataQuality.WARN
            ml_detail = "ML confidence not recorded; treat model output as unvalidated."
        elif detection_confidence >= settings.PROD_CONFIDENCE_MIN:
            ml_grade = DataQuality.PASS
            ml_detail = f"ML confidence {detection_confidence:.2f} meets production minimum {settings.PROD_CONFIDENCE_MIN:.2f}."
        elif detection_confidence > 0.0:
            ml_grade = DataQuality.WARN
            ml_detail = f"ML confidence {detection_confidence:.2f} below production minimum {settings.PROD_CONFIDENCE_MIN:.2f}."
        else:
            ml_grade = DataQuality.FAIL
            ml_detail = "ML confidence is zero; output carries no usable confidence value."
        checks.append({"source": "model", "grade": ml_grade.value, "detail": ml_detail})
        grades.append(ml_grade)

        # --- Environmental forcing ---
        if env_quality is None:
            env_grade = DataQuality.WARN
            env_detail = "Environmental forcing quality not available; reanalysis values are unverified for this window."
        else:
            env_grade = DataQuality(env_quality.get("overall", "WARN"))
            env_detail = "Environmental forcing quality: " + "; ".join(
                f"{c['name']}={c['quality']} ({c['detail']})" for c in env_quality.get("checks", [])
            ) or env_quality.get("overall", "unknown")
        checks.append({"source": "environmental", "grade": env_grade.value, "detail": env_detail})
        grades.append(env_grade)

        # --- Drift simulation ---
        if drift_ok is None:
            drift_grade = DataQuality.FAIL
            drift_detail = "No drift simulation result available; origin inference cannot be supported."
        elif drift_ok:
            drift_grade = DataQuality.PASS
            drift_detail = "Deterministic drift simulation produced an origin region and uncertainty polygon."
        else:
            drift_grade = DataQuality.FAIL
            drift_detail = "Drift simulation reported failure; origin region cannot be inferred."
        checks.append({"source": "drift", "grade": drift_grade.value, "detail": drift_detail})
        grades.append(drift_grade)

        # --- AIS coverage ---
        if ais_track_count is None:
            ais_grade = DataQuality.WARN
            ais_detail = "No AIS query performed; vessel correlation unavailable."
        elif ais_track_count > 0:
            ais_grade = DataQuality.PASS
            ais_detail = f"AIS correlation scanned {ais_track_count} vessel track(s) in the search window."
        else:
            ais_grade = DataQuality.WARN
            ais_detail = "AIS query returned zero vessel tracks in the search window; candidate identification limited to no vessels."
        checks.append({"source": "ais", "grade": ais_grade.value, "detail": ais_detail})
        grades.append(ais_grade)

        overall = cls._worst(grades)

        return {
            "overall": overall.value,
            "sources": checks,
            "coverage": {
                "satellite": detection_status is not None,
                "environmental": env_quality is not None,
                "drift": drift_ok is not None,
                "ais": ais_track_count is not None,
            },
            "note": (
                "Overall data quality is the strict worst-case grade across contributing sources. "
                "A grade below PASS means the affected downstream inference should be treated as provisional."
            ),
        }