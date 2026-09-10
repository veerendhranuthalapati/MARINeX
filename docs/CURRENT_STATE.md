# MARINeX Current State

_SIH 2026 — PS ID SIH26143 — Team DOOM CODERS (Team ID 120462)._

## Build Status
| Component | Status |
|-----------|--------|
| Backend Python (FastAPI) | ✅ 19/19 tests passing |
| Frontend TypeScript (React/Vite) | ✅ Typechecks clean (tsc --noEmit, 0 errors) |
| ML Training Campaign (Phases 1–11) | 🚧 Running (phase [9] multi-seed stability) |
| Dataset (120 patches) | ✅ Group-aware split, zero leakage |
| Frozen test (base UNet = FINAL) | IoU=0.8857 Dice=0.9394 Prec=0.9080 Rec=0.9731 ECE=0.1754 |

## Architecture
- **Backend**: FastAPI + SQLAlchemy + SQLite (local) / PostgreSQL+PostGIS (Docker)
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + Leaflet + MapLibre
- **ML**: PyTorch (U-Net FINAL, U-Net++, SegFormer) + deterministic drift/attribution services
- **Deployment**: Docker Compose (PostGIS 16 + backend + frontend)

## API Surface (86 routes, mounted on both `/api/v1` and `/api`)
- **Incidents** (incident-centric investigation): `POST/GET/PATCH /incidents[/{id}]`, `POST /incidents/{id}/scenes`, `POST /incidents/{id}/detect`, `GET/POST /incidents/{id}/evidence`, `GET /incidents/{id}/detection-runs`, `GET /incidents/{id}/drift-reports`, `GET /incidents/{id}/attribution`, `GET /incidents/{id}/origin`, `GET /incidents/{id}/report`
- **Async jobs**: `POST /jobs`, `GET /jobs[/{job_id}]`, `POST /jobs/{job_id}/run` (detection/drift/attribution/environment/report stages run in background thread)
- **Explainability**: `POST /explainability/run` (occlusion + Grad-CAM heatmaps, provenance JSON)
- **Classic pipelines** (slick-scoped): `/scenes`, `/detection`, `/slicks`, `/drift`, `/environment`, `/attribution`, `/reports`, `/ais`, `/investigations`, `/candidates`, `/health`, `/demo`
  - `POST /demo/seed` now incident-centric: creates `incident_sih26143_mumbai_offshore_001`, binds scene + slicks, sets UNDER_INVESTIGATION.

## Frontend Pages (9)
Dashboard, Scenes, Detection, Drift, Investigation, Candidates, Reports, AIS Analysis, Settings (+404).
Dashboard is incident-centric: seeds demo data if empty, then renders incident slicks, environment + candidate focus on the primary slick.

## ML Campaign State (phase [9] of 11)
- [1] Split + leakage: clean. [2] Architecture → `unet`. [3] Ablations (channels/loss/aug). [4] Preprocessing → percentile. [5] Hard-negative mining + retrain. [6] Two-stage. [7] Calibration valid: **ECE raw 17.35% → calibrated 0.46% (T=0.226), Brier 0.0330 → 0.0025**. [8] Frozen test locked decisions.
- [9] Multi-seed stability (seeds 42/123/999) — in progress on CPU; a silent OOM kill wiped mid-run twice under disk-full conditions; resolved by freeing disk, capping torch intra-op threads, and freeing retained training-state models before [9].
- [10] Robustness + cross-dataset (sentinel1_external, 40 samples). [11] Exports.

## Known Limitations
- SQLite demo mode (no PostGIS); Postgres via Docker for spatial mode.
- CPU-only training/inference (torch 2.14.0+cpu); campaign phases [2]–[9] cost ~45–55 s/epoch for UNet.
- AIS ranking is an interpretable weighted evidence score (no local archive of full MarineCadastre history).
- Chunk size warning on build (1.9 MB JS bundle) — code splitting recommended for production.

## Provenance & Reproducibility
- Checkpoints: `models/campaign/*.pt` (gitignored) + `*.done` resume markers.
- Reports: `reports/{campaign_summary,calibration,robustness,hard_negatives,explainability}.*`.
- Evidence ledger carries `StatusLabel` (OBSERVED/ML_SEGMENTED/INFERRED/SIMULATED/TRACKED/CANDIDATE/DEMO_DATA) + provenance on every fact; the system never frames a candidate as guilty.