"""Scientific status labels and provenance helpers.

Every result shown across the stack must carry one of these status labels so
the UI never overstates what the data actually proves. Nothing here is inferred
from models that were not run.
"""

from enum import Enum


class StatusLabel(str, Enum):
    OBSERVED = "OBSERVED"             # sensor-observed fact (satellite, AIS)
    ML_SEGMENTED = "ML_SEGMENTED"     # satellite slick produced by the ML model
    INFERRED = "INFERRED"             # derived from a model (e.g. origin region)
    SIMULATED = "SIMULATED"           # physics simulation (drift)
    PREDICTED = "PREDICTED"           # model prediction output
    TRACKED = "TRACKED"               # AIS vessel position report
    CANDIDATE = "CANDIDATE"           # ranked investigation candidate (not guilt)
    DEMO_DATA = "DEMO_DATA"           # synthetic/demo data, never real
    NOT_AVAILABLE = "NOT_AVAILABLE"
    MOCK = "MOCK"
    EXPERIMENTAL = "EXPERIMENTAL"
    UNVALIDATED = "UNVALIDATED"


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    EXCLUDED = "EXCLUDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_RELIABLE_CANDIDATE = "NO_RELIABLE_CANDIDATE"


class DataQuality(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class Provenance:
    """Factory that stamps a provenance dict on every major pipeline output.

    Fields (Phase 23):
      source, source_version, model_id, model_version, config, processing_stage,
      preprocessing_version, created_at, schema_version
    """

    SCHEMA_VERSION = "1.0"

    @staticmethod
    def stamp(
        source: str,
        source_version: str,
        processing_stage: str,
        model_id: str | None = None,
        model_version: str | None = None,
        config: dict | None = None,
        preprocessing_version: str | None = None,
        created_at: str | None = None,
    ) -> dict:
        return {
            "source": source,
            "source_version": source_version,
            "model_id": model_id,
            "model_version": model_version,
            "config": config or {},
            "processing_stage": processing_stage,
            "preprocessing_version": preprocessing_version,
            "created_at": created_at,
            "schema_version": Provenance.SCHEMA_VERSION,
        }


def make_provenance(**kwargs) -> dict:
    return Provenance.stamp(**kwargs)