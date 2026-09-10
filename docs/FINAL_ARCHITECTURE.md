# MARINeX Final Architecture (SIH26143)

Closing architecture reference for the final validation phase. Supersedes the
schematic claims in `docs/architecture.md` where numbers differ; it points to
measured, re-verified facts.

## 1. System scope

MARINeX: *use satellite imagery to determine oil spills at sea and correlate AIS
data to identify the responsible vessel* (SIH26143). The system is an
incident-centric investigation platform: `Scene → Detection →
Characterization → Drift → AIS → Attribution → Report`.

## 2. Components (as implemented and tested)

| Layer | Component | Notes |
|---|---|---|
| API | FastAPI `backend/app/main.py` + `api/v1/*` routers | demo, incidents, scenes, jobs, explainability, model-card endpoints |
| Detector | `backend/app/services/detection/production_ml.py` | frozen PyTorch U-Net `marinex-unet-v1.0.0`, threshold 0.70, T=0.2262; `_find_ml_root()` resolves `ml/` for model registry + transforms |
| Detector (alternates) | `classical_baseline.py`, `mock.py` | Otsu baseline & deterministic test detector |
| Characterization | `characterizer.py` | geodesic area (km²), perimeter, centroid, OBB, compactness (WGS-84) |
| Drift | `drift/service.py` (MockDriftService) | LAGRANGIAN_MONTE_CARLO_DRIFT_v1; HINDCAST + FORECAST; wind leeway α=0.032, D=10 m²/s; RNG-seeded deterministic |
| Environment | `environmental/service.py`, `quality.py` | sample snapshot forcing; FAIL grade blocks simulation (HTTP 422) |
| AIS | `ais/csv_provider.py` + `ml/ais/*` (DuckDB engine) | MarineCadastre-format CSV; year/month/day parquet partitions; schema validate + clean + gap-aware segmentation; velocity-agnostic haversine math |
| Attribution | `attribution/engine.py` | proximity/temporal/trajectory/behavior weighted scores (0.35/0.25/0.25/0.15) → CANDIDATE_IDENTIFIED / INSUFFICIENT_EVIDENCE / NO_RELIABLE_CANDIDATE |
| Data quality | `data_quality/service.py` | per-source grades (satellite/model/environmental/drift/AIS), strict worst-case overall |
| Evidence ledger | `EVIDENCE.md` | append-only OBSERVED/ML_SEGMENTED/INFERRED/SIMULATED/TRACKED/CANDIDATE/DEMO_DATA records + provenance JSON |
| ML campaign | `ml/` (train, evaluate, models.registry, data.transforms, metrics) | CPU campaign, seeds 42/123/999 |
| Frontend | React + Vite + TS `frontend/` | Command center, model intelligence, explainability, evidence graph, demo runner (route changes committed `8f5a18d`) |
| Report generator | `scripts/run_pipeline_cli.py`, `jobs` router | end-to-end CLI + async stage jobs (`get_engine_url()` background sessions) |

## 3. Data flow (verified end-to-end)

`scripts/run_pipeline_cli.py` ran the full chain on a fresh-schema SQLite DB:
Scene → Detection → Characterization (slick area 9.80 km²) → Drift →
AIS (5 vessels scanned) → Attribution (primary suspect PACIFIC CROWN, forensic
evidence score 40.6/100) → Investigation Report REP-SLICK_SC-20260910, status
SUCCESS (2026-09-10).

## 4. ML layer (canonical numbers)

- ADAPTERS apply identical `SARPreprocessor(strategy="percentile")` contract
  `[VV, VH, VV−VH]`; single-band replicated (channel_note).
- Selected: **unet (FINAL) frozen th=0.70**, test IoU 0.8857 / Dice 0.9394;
  unet_plus_plus 0.9175 (val-best th=0.55); Two-Stage 0.8769 — reported as
  alternative paths, selection decision was on **validation only**.
- Probability calibration: temperature log-space T=0.2262, ECE 0.1735→0.0046,
  Brier 0.0330→0.0025.
- Full table: `reports/final_model_benchmark.md`.

## 5. Drift & AIS constraints (honest)

- Drift forcing is a fixed sample-environment snapshot with seeded RNG:
  deterministic, not reanalysis-fed (`docs/DRIFT.md`, `docs/DRIFT_VALIDATION.md`).
- AIS archive is broadcast-only, local sample-sized, partitioned to parquet;
  dark vessels are uncatalogued; a zero-track window yields
  `NO_RELIABLE_CANDIDATE`, never an invented suspect (`docs/AIS.md`,
  `docs/AIS_VALIDATION.md`).
- All drift/attribution output is labeled SIMULATED / INFERRED / TRACKED on the
  evidence ledger; attribution is decision-support, never adjudication.

## 6. Deployment notes

- Backend: read `backend/.env.example`; dev DB is local SQLite
  (`sqlite:///./marinex.db`, path resolves at repo root when running scripts and
  at `backend/` when running uvicorn — rebuild stale DBs via
  `scripts/seed_demo_data.py`; do not patch old-schema files).
- Frontend: `npm run build` (tsc + vite); dev proxy `/api → localhost:8000`.
- E2E: `scripts/run_pipeline_cli.py` after seeding.