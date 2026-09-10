# MARINeX Evidence Ledger (SIH26143)

The evidence ledger (Phases 21-22) is the append-only factual backbone of every
investigation. Every pipeline stage - detection, characterization, environment,
drift, AIS, attribution, report - appends a structured `EvidenceRecord` to the
incident ledger so an analyst sees exactly what was observed / inferred /
simulated, with provenance, confidence, and a status label.

## 1. Record Types

`EvidenceService` (`backend/app/services/evidence.py`) emits:

| Type | Produced by | Example |
|---|---|---|
| `DETECTION` | `record_detection` | ML segmentation run (model, confidence, oil pixels, artifact, slick ids). |
| `SLICK` | `record_characterization` | Geodesic area, morphometrics for a slick. |
| `ENVIRONMENT` | `record_environment` | Wind/current u-v vectors, provider, quality grade. |
| `DRIFT` | `record_drift` | Hindcast/forecast origin centroid + time, parameters, uncertainty. |
| `AIS` | `record_ais` | Vessel-track count in the spatial-temporal query window. |
| `CANDIDATE` | `record_attribution` | Ranked candidates with per-factor scores. |

Analysts may additionally append manual records via
`POST /api/v1/incidents/{id}/evidence` (e.g. inspection report notes).

## 2. Status Labels

Every record carries one `StatusLabel` (see `backend/app/core/status.py`):
`OBSERVED`, `ML_SEGMENTED`, `INFERRED`, `SIMULATED`, `PREDICTED`, `TRACKED`,
`CANDIDATE`, `DEMO_DATA` (+ supplementary `NOT_AVAILABLE`, `MOCK`,
`EXPERIMENTAL`, `UNVALIDATED`). The label binds each fact to how it was
produced - nothing on the ledger claims more than its producing stage supports.

## 3. Provenance Schema

`Provenance.stamp()` (`backend/app/core/status.py`, `schema_version = "1.0"`)
stamps every major output:

| Field | Example |
|---|---|
| `source` | `Sentinel-1 C-SAR`, `MARINeX-Attribution`, `LAGRANGIAN_MONTE_CARLO_DRIFT_v1` |
| `source_version` | `v1` |
| `model_id` | adapter/algorithm id (e.g. `unet`) |
| `model_version` | model/architecture id (e.g. `marinex-unet-v1.0.0`) |
| `config` | run config (artifact path, weights, direction, query window) |
| `processing_stage` | e.g. `detection`, `characterization`, `environment`, `drift`, `ais`, `attribution` |
| `preprocessing_version` | e.g. `percentile` |
| `created_at` | ISO-8601 timestamp of the stamp |
| `schema_version` | `1.0` |

## 4. JSON-Safe Serialization

`EvidenceRepository.create` (`backend/app/repositories/evidence_repo.py`) routes
every `value` and `provenance` payload through `json_safe()`, which recursively
converts datetimes to ISO-8601 strings, numpy scalars via `.item()`, and
normalizes dicts/lists/tuples. The ledger therefore always serializes cleanly to
JSON regardless of how a stage constructed its payload.

## 5. Idempotence & Resilience

- **Append-only, stage-keyed**: re-running a stage appends a new record with the
  stage + timestamp, it never mutates or deletes prior records.
- **Record creation cannot break the pipeline**: `EvidenceService._record`
  warns and skips when no `incident_id` is supplied, and catches any exception
  from persistence, logging the error and returning `None` - evidence recording
  failure never aborts the upstream scientific stage.
- Demo seeding (`POST /api/v1/demo/seed`) is idempotent: incidents, scenes, and
  detection runs are only created if absent.

## References

- `backend/app/services/evidence.py` - `EvidenceService`
- `backend/app/schemas/evidence.py` - record create/response schemas
- `backend/app/repositories/evidence_repo.py` - `json_safe` + `EvidenceRepository`
- `backend/app/core/status.py` - `StatusLabel`, `DataQuality`, `Provenance`
- `backend/app/api/v1/incidents.py` - evidence endpoints on the incidents API