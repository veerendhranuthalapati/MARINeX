# MARINeX Current State

_SIH 2026 - PS ID SIH26143 - Team DOOM CODERS (Team ID 120462)._
_Last updated with commit f764d88 (incident-centric investigation pipeline +
frozen UNet campaign)._

## Build Status

| Component | Status |
|---|---|
| Backend Python (FastAPI) | 35/35 tests passing |
| Frontend TypeScript (React/Vite) | Typecheck clean (`tsc --noEmit`, exit 0) + production build OK |
| Production ML model | Frozen (`marinex-unet-v1.0.0`), calibrated |
| Dataset (sentinel1-primary) | 120 samples, group-aware 80/20/20 split, zero leakage |
| Reports | Scientific validation + audit artifacts under `reports/` |

## ML Model (frozen)

- **Artifact**: `models/best_model/marinex_unet_v1.pt` + `models/production/metadata.json`
- **Architecture**: UNetBaseline, 3 channels `[VV, VH, VV-VH]`, percentile
  preprocessing, threshold 0.70, calibration temperature 0.2262.
- **Frozen test metrics**: IoU 0.8857, Dice 0.9394, Precision 0.9080,
  Recall 0.9731, FPR 0.0041, object-F1 0.7901.
- **Calibration**: ECE 0.1735 -> 0.0046; Brier 0.0330 -> 0.0025.
- **Multi-seed val**: seed 42 (0.9459 / 0.9722), seed 123 (0.9358 / 0.9668),
  seed 999 (0.9265 / 0.9619) IoU / Dice.
- **Cross-dataset**: external Singapore Strait IoU 0.8487 / Dice 0.9181.

## Completed Phases

- Satellite ingestion & scene management
- ML detection (production UNet wired) + characterization (geodesic area,
  perimeter, compactness)
- Drift hindcast/forecast (Lagrangian, deterministic) + physics/determinism/
  sensitivity validation
- AIS provider + corridor queries + data-quality audit + trajectory validation
- Explainable 4-factor attribution + conclusion tiers
- Forensic report generation
- Incident-centric investigation API + async jobs
- Evidence ledger with provenance (DETECTION / SLICK / ENVIRONMENT / DRIFT /
  AIS / CANDIDATE)
- Incident uncertainty + Data Quality Service (per-source grades, strict
  worst-case overall)
- Demo cases A-D + `incident_complete` (`POST /api/v1/demo/cases/{id}`, all
  inputs labeled DEMO_DATA, real computations)
- ML validation campaign (robustness, scene-level, slick-size, look-alike,
  geometry, error taxonomy, cross-dataset) + explainability validation suite
- Frontend pages incl. ML Intelligence, Explainability, and Evidence Graph

## Demo Cases Available

| Case | Behavior |
|---|---|
| `case_a_high_confidence` | DEMO tanker crossing origin -> `CANDIDATE_IDENTIFIED` (HIGH) |
| `case_b_low_confidence` | +3 dB degraded raster -> `LOW_CONFIDENCE` gate (analyst review, no auto-attribution) |
| `case_c_multi_candidate` | Standard corridor, 5 vessels ranked with honest conclusion |
| `case_d_no_candidate` | Remote slick -> `NO_RELIABLE_CANDIDATE` |
| `incident_complete` | Full evidence chain + report + evidence ledger + provenance |

## Known Limitations (honest)

- **Drift**: `MockDriftService` is deterministic and reproducible but is not
  driven by live reanalysis fields and does not propagate forcing uncertainty;
  the ERA5/CMEMS adapter is stubbed.
- **AIS**: coverage is an archived broadcast-style CSV sample of MarineCadastre
  histories; dark vessels (transponder off / absent) are uncatalogued and cannot
  be scored. No live AIS streaming yet.
- **Explainability**: the perturbation test passes (~0.055 confidence drop) but
  the randomization test is WEAK - saliency maps for the production UNet must
  not be over-interpreted.
- SQLite is the default local store (full PostGIS via Docker Compose).
- CPU-only inference/training.

## Pending

- Final review, commit, and push of the current working tree to
  `origin` (https://github.com/veerendhranuthalapati/MARINeX.git).
  See `docs/QUALITY_GATE.md` (31-item gate; only the commit/push item remains).

## References

- `docs/QUALITY_GATE.md` - release checklist
- `docs/INVESTIGATION_WORKFLOW.md` - scientific pipeline and gating
- `docs/CURRENT_STATE.md` (this file) - status snapshot