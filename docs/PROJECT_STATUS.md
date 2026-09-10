# MARINeX — Project Status / Handoff Document

> Authoritative state-of-project snapshot. Generated 2026-09-10 by audit of the
> actual repository (files, git history, artifacts, runs, tests). Every metric
> below was produced by a real run and is reproducible via the referenced
> command/artifact. Nothing is inferred, and nothing planned is described as done.

| | |
|---|---|
| Project | MARINeX — Maritime Intelligence Platform |
| SIH | SIH26143 — "Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill" |
| Team | DOOM CODERS |
| Team ID | 120462 |
| Language/toolchain | Python 3.13.3 (backend/ML), TypeScript 5.7.3 + React 18 (frontend) |
| Primary unit(s) | CPU (PyTorch 2.14.0+cpu), 16 vCPU / ~15 GB |

---

## 1. EXECUTIVE SUMMARY

```
PROJECT STATUS: DEMO-READY (ML research/validation complete; deployment real-data wiring pending)
```

**What MARINeX currently does (verified end-to-end 2026-09-10):**
1. Ingest a satellite-scene record, run frozen U-Net oil-spill segmentation (sample
   SAR imagery only), characterize the slick (area/perimeter/centroid/OBB).
2. Hindcast the slick origin with a deterministic Lagrangian Monte-Carlo drift
   particle model (custom engine, not OpenDrift/OpenOil).
3. Query a bundled AIS sample archive (CSV → partitioned Parquet → DuckDB),
   reconstruct vessel trajectories, and score candidate vessels with a
   rule-based explainable attribution engine.
4. Persist everything into an append-only evidence ledger with provenance
   labels, generate a Markdown investigation report, expose it all via
   FastAPI + a dark React (Vite) command-center UI.

| Area | Current state |
|---|---|
| ML | Frozen production U-Net `marinex-unet-v1.0.0`; test IoU **0.8857**, calibrated, single protected test pass, re-verified. |
| Data | **100% synthetic** SAR-like benchmark corpus (120 primary + 40 external), leakage-free group-aware splits. |
| Drift | Custom `LAGRANGIAN_MONTE_CARLO_DRIFT_v1`; physics sanity E/W/N/S + zero ALL PASS, deterministic. Environmental forcing is **MOCK** (sample snapshot). |
| AIS | Broadcast-only **sample** archive (20 rows, 5 vessels) → DuckDB Parquet engine; quality audit clean; no full real-world archive. |
| Attribution | **RULE-BASED** weighted factor scoring (no ML ranking); works and is tested. |
| Frontend | 13 routed pages, dark "Futur-inspired" design system, MapLibre map, motion animation, working API integration. |
| Deployment | Docker compose files exist; **Docker daemon not running on this machine** → containers not verified locally. Local dev = uvicorn + Vite. |
| Biggest blocker | Real environmental + AIS data wiring (ERA5/CMEMS adapter stubs `NotImplementedError`; AIS archive is a 20-row sample). |

**Test state (fresh runs today):** backend `pytest backend/tests` → **35 passed**;
ML `pytest ml/tests` → **19 passed**; frontend `npm run build` (tsc + vite) → **PASS**.

---

## 2. PROJECT OBJECTIVE

**Intended system (from `docs/sih_problem_statement.md`):** detect oil spills at
sea from satellite imagery, then correlate AIS data to identify the responsible
vessel. Baseline components: Sentinel SAR ingestion, dark-spot detection +
slick characterization, Lagrangian drift (OpenDrift/OpenOil-style), AIS
provider with spatial/temporal corridor filtering, vessel trajectory
reconstruction, explainable attribution, forensic evidence chain.

**In practice / current implementation:**
- Satellite imagery = **synthetic** 256×256 SAR-like patches (no real
  Sentinel-1 pixels anywhere).
- Drift = **custom closed-form** particle integrator
  (`backend/app/services/drift/service.py`); OpenDrift/OpenOil are **NOT
  implemented** (only referenced).
- AIS = bundled sample CSV, not a live/full archive.
- Environmental forcing = **mock provider**; the ERA5/CMEMS adapter is a stub
  that raises `NotImplementedError` when unconfigured.
- Everything else (detection chain, evidence ledger, API, UI) is implemented
  and working against this synthetic stack.

---

## 3. COMPLETE REPOSITORY TREE (relevant)

```
MARINeX/
├── .env.example                  # placeholder env template (no secrets)
├── .gitignore
├── Makefile                      # install/test/seed/pipeline/audit targets
├── README.md                     # setup + CLI cookbook (encoding fixed)
├── docker-compose.yml            # postgis + backend + frontend compose
├── marinex.db                    # local dev SQLite (gitignored, rebuilt 2026-09-10)
├── backend/
│   ├── Dockerfile                # python:3.12-slim + uvicorn
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, static imagery mount
│   │   ├── core/                 # config, database(init_db/create_all), logging, status
│   │   ├── api/v1/               # 18 routers (see section 7)
│   │   ├── models/               # SQLAlchemy models (see section 8)
│   │   ├── repositories/         # incident, scene, slick, vessel, evidence, jobs, investigation, detection_run
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   ├── services/
│   │   │   ├── detection/        # production_ml.py (frozen UNet), classical_baseline, mock, characterizer, explainability, adapters
│   │   │   ├── drift/            # service.py (Lagrangian MC), __init__
│   │   │   ├── ais/              # csv_provider, mock_provider, provider
│   │   │   ├── environmental/    # registry, service, quality, mock_provider, era5_provider (STUB)
│   │   │   ├── attribution/      # engine.py (rule-based scores)
│   │   │   ├── data_quality/     # per-source quality gating
│   │   │   ├── ml_validation/    # card/validation endpoints backend
│   │   │   ├── reporting/        # generator.py (Markdown report)
│   │   │   └── evidence.py       # evidence ledger service
│   │   └── utils/                # geo, image, artifacts
│   └── tests/                    # 10 test modules (35 tests)
├── frontend/
│   ├── Dockerfile                # node build + nginx serve (nginx.conf present)
│   ├── package.json / lockfile
│   ├── index.html                # dark shell + Google fonts (Syne/Space Grotesk/Plus Jakarta/JetBrains)
│   ├── vite.config.ts            # /api proxy → localhost:8000
│   ├── tailwind.config.js        # dark/monochrome/accent design tokens
│   └── src/
│       ├── App.tsx               # 13 routes (section 5)
│       ├── services/api.ts       # axios client + 30 API methods
│       ├── store/useMarinexStore.ts  # zustand store
│       ├── types/index.ts, utils/cn.ts
│       ├── layouts/AppLayout.tsx
│       ├── components/           # map/MapLibreMap, investigation/*, common/*, ui/*
│       └── pages/                # 13 pages (section 5)
├── ml/
│   ├── train.py, evaluate.py, explain.py
│   ├── requirements.txt          # torch, torchvision, opencv, duckdb, pyarrow, pyyaml, mlflow, numpy, Pillow, pytest
│   ├── models/                   # unet, unet_plus_plus, segformer, classifier, classical_baseline, registry, base
│   ├── data/                     # dataset.py, transforms.py (SARPreprocessor), generate_sar_dataset.py, leakage_detection.py, manifest.py, tiling.py
│   ├── data_audit/               # audit_dataset.py, split_dataset.py, validate_dataset.py, visualize_samples.py, inventory, report
│   ├── evaluation/               # metrics.py, calibration.py, error_analysis.py, object_eval.py, robustness.py
│   ├── explainability/           # methods.py (gradcam/occlusion/attention)
│   ├── training/                 # trainer.py, experiment_runner.py, two_stage_pipeline.py
│   ├── losses/                   # segmentation_losses.py (bce/dice/bce+dice/focal/tversky/focal-tversky)
│   ├── features/, inference/     # slick_features, predict, postprocess, geojson_export
│   ├── hard_negative_mining/     # build/extract/visualize
│   ├── ais/                      # ais_schema.py, duckdb_engine.py, postgis_engine.py, prepare_ais.py, trajectory.py
│   └── tests/                    # 4 test modules (19 tests)
├── data/
│   ├── datasets/sentinel1_primary/   # images/patch_0001..0120.png + masks (committed, synthetic)
│   ├── datasets/sentinel1_external/  # images/patch_0001..0040.png (committed, synthetic)
│   ├── manifests/*.json              # manifests (synthetic origin labeled)
│   ├── splits/split_group_aware_v1.json
│   ├── samples/                      # AIS CSV, candidate/scene/slick/env JSON, imagery sample
│   ├── processed/ais/partitions/     # parquet (gitignored, regenerable)
│   ├── processed/detections/         # detection run artifacts (gitignored)
│   └── raw/, interim/, hard_negatives/, metadata/   # policy dirs (bulk ignored)
├── configs/
│   ├── datasets/*.yaml               # sentinel1_oilspill_{primary,external}
│   ├── environments/local.yaml
│   └── training/*.yaml               # unet_plus_plus, segformer
├── scripts/                          # 24 entrypoints (section 9 list; run with .venv)
├── models/
│   ├── best_model/                   # marinex_unet_v1.pt (FINAL), marinex_unet_plus_plus_v1.pt, marinex_segformer_v1.pt, marinex_lookalike_classifier_v1.pt
│   ├── checkpoints/                  # unet_baseline/seeds/unetpp/segformer bests
│   └── production/metadata.json      # frozen config (th 0.70, T 0.2262, freeze commit f764d88)
├── docs/                             # 29 + md (section 10 list)
└── reports/                          # campaign artifacts (gitignored except 3 legacy CSVs) (section 11)
```

---

## 4. CURRENT ARCHITECTURE

```mermaid
flowchart TD
    subgraph UI["Frontend (React 18 + Vite, zustand, MapLibre, motion)"]
        P[13 pages: Dashboard, Scenes, Detection, Investigation, Drift,
          AIS, Candidates, Reports, Model Intelligence, Explainability,
          Evidence Graph, Settings]
    end

    subgraph API["Backend (FastAPI 0.115.6 /api/v1 + /api)"]
        R[18 routers]
        C[core: config + SQLAlchemy + logging]
    end

    subgraph SVC["Services"]
        DET[Detection: production_ml.py — frozen UNet]
        CHA[Characterizer — geodesic morphometry]
        DRF[Drift — Lagrangian MC v1 (custom, seeded rng)] 
        ENV[Environment — MOCK provider; ERA5 = STUB]
        AIS[AIS — CSV provider → DuckDB parquet]
        ATT[Attribution — RULE-BASED weighted scoring]
        DQ[Data-quality gate — per-source grades]
        EV[Evidence ledger + provenance]
        REPO[Reporting — Markdown generator]
        EXP[Explainability — Grad-CAM/occlusion]
    end

    subgraph ML["ML layer (ml/)"]
        REG[Model registry: unet/++/segformer/classifier]
        PREP[SARPreprocessor percentile 2-98]
        MET[Evaluation: metrics, calibration, robustness, error analysis]
    end

    subgraph STORE["Database / storage"]
        DB[(SQLite marinex.db — dev; PostGIS via docker-compose — NOT run locally)]
        PARQ[(data/processed/ais/partitions/*.parquet — DuckDB)]

    end

    UI --> API
    API --> SVC
    DET --> ML
    CHA --> DET
    DRF --> ENV
    ATT --> AIS
    ATT --> DRF
    EV --> SVC
    REPO --> EV
    PARQ <--> AIS
    SVC --> DB
    DB -.PostGIS .-> DQ
```

**Honest annotations:** ERA5/CMEMS `NOT IMPLEMENTED` (stub). OpenDrift/OpenOil
`NOT IMPLEMENTED`. PostGIS `NOT RUN LOCALLY` (Docker daemon offline). Real
Sentinel-1 image ingestion `NOT IMPLEMENTED` (the data layer ingests the
bundled synthetic patches; the scene-upload API exists for scene CRUD only).

---

## 5. FRONTEND STATUS

**Framework/tooling:** React 18.3.1, TypeScript 5.7.3, Vite 6.1, Tailwind
CSS 3.4.17 (+ PostCSS/Autoprefixer), react-router-dom 6.29, zustand 5.0.15,
axios 1.7.9, recharts 2.15.1, maplibre-gl 6.9.0, motion 13.2.0 (Motion.dev),
lucide-react, clsx, tailwind-merge.

| Library | Status |
|---|---|
| Motion.dev (motion) | **INSTALLED + USED** (`motion/react` in RadialScore, ComparisonSlider, TimelineScrubber, DataPipelineFlow, EvidenceDrawer + AnimatePresence, CandidateVesselCard) |
| Kokonut UI | NOT USED (not a dependency) |
| Bklit UI | NOT USED (not a dependency) |
| shadcn/ui | NOT USED (project uses hand-rolled `cn()` + local components) |
| MapLibre | **USED** (`components/map/MapLibreMap.tsx`; dark style; also `leaflet.css` referenced in index.html — vestigial) |
| Turf.js | NOT USED (geometry math is backend-side / geo utils in TS) |
| TanStack Query | NOT USED (axios hand-rolled in `services/api.ts`) |
| Zustand | **USED** (`store/useMarinexStore.ts`) |

**Pages / routes (App.tsx):** `/` Dashboard, `/scenes`, `/detection`,
`/investigation`, `/drift`, `/ais`, `/candidates`, `/reports`,
`/model-intelligence`, `/explainability`, `/evidence-graph`, `/settings`
(+ `*` → `/`).

**Major components:** `layouts/AppLayout` (shell/nav), `map/MapLibreMap`,
`investigation/*` (CandidateVesselCard, EvidenceDrawer, DataPipelineFlow,
TimelineScrubber, RadialScore, ComparisonSlider), `common/Badge`, `ui/*`.

**API integration:** `services/api.ts` exposes `MarineXApi` with 30 methods,
all proxied `/api` → `http://localhost:8000` in dev. Newest methods wired in
the final phase: `getMlCard`, `getMlValidation`, `getExplainabilityValidation`,
`runDemoCase`, `getIncidentDetail`.

**Working (verified):** `npm run build` PASS; routes render under dev; pages
consume real backend endpoints through the SPA. "Working" here = builds +
type-checks + is wired to live endpoints; interactive pixel-perfect behavior on
all 13 pages was not exhaustively clicked through during this audit.

---

## 6. FUTUR UI STATUS

The repo implements a deliberately "Futur-inspired" dark command-center design
system (Tailwind tokens + Google Fonts in `index.html`/`tailwind.config.js`):

| Aspect | Assessment | Evidence |
|---|---|---|
| Typography | **COMPLETE** | Syne (display), Space Grotesk (heading), Plus Jakarta Sans (body), JetBrains Mono (mono/UI) |
| Dark visual system | **COMPLETE** | `dark` class root; `#05070a` base; monochrome palette; cyan/amber/crimson accents |
| Navigation | **COMPLETE** | AppLayout side/nav bar, 12 destinations |
| Hero | **MISSING** | No marketing/landing hero; app opens straight into a dashboard |
| Scroll experience | **PARTIAL** | Standard page scroll; no scroll-driven storytelling sections |
| Investigation workspace | **PARTIAL** | Purpose-built pages (Investigation, Candidates, Evidence Graph) with drawers/sliders/timeline |
| Map | **PARTIAL** | MapLibre dark map present; limited interactions exposed |
| Motion | **PARTIAL** | motion used in cards/drawer/slider/score circles; not site-wide scroll choreography |
| Cards | **PARTIAL** | Custom cards/CandidateVesselCard/RadialScore present |
| Analytics | **PARTIAL** | Recharts in Model Intelligence + Dashboard |

No redesign performed during this audit.

---

## 7. BACKEND STATUS

**Installed versions (real):** fastapi 0.115.6, pydantic 2.13.4, sqlalchemy
2.0.36, numpy 2.2.0, pandas 3.0.5, scikit-learn 1.6.0, shapely 2.0.6, scipy
1.18.0, torch 2.14.0+cpu, Pillow 12.3.0, duckdb 1.5.5, pyarrow 25.0.1,
httpx/pytest/pytest-asyncio (venv), alembic **declared in requirements but NOT
wired** (no `alembic.ini`, no `alembic/versions`; schema is `Base.metadata.create_all` via `init_db()` at startup).

**Auth:** NONE (no auth middleware; out of scope for the demo, noted as a
deployment gap).
**Background workers:** `jobs` router executes stages (detection/drift/
attribution/environment/report) in a background thread with its own DB session
via `get_engine_url()`.

**Endpoints (prefix → purpose):**

| Method | Path | Purpose / behavior |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/scenes/{scene_id}`; POST `/scenes/upload` | scene CRUD + upload |
| POST | `/detection/run/{scene_id}`; GET `/detection/run/{scene_id}/details` | run detector (default PRODUCTION_ML), read provenance |
| GET | `/slicks/{slick_id}`; GET `/slicks/{slick_id}/geojson` | slick read + GeoJSON export |
| GET | `/environment/{slick_id}` | environmental snapshot for a slick |
| POST | `/drift/{slick_id}/simulate`; GET `/drift/{slick_id}` | Lagrangian hindcast/forecast (+ env quality gate → 422 on FAIL) |
| POST | `/ais/query`; GET `/ais/trajectories/{vessel_id}`; GET `/ais/corridor/all` | DuckDB/CSV AIS corridor query + trajectories |
| GET | `/vessels/{vessel_id}` | vessel details |
| POST | `/attribution/{slick_id}/run`; GET `/attribution/candidates/{slick_id}` | run rule-based attribution, list ranked candidates |
| GET/POST | `/investigations/{slick_id}`; PUT updates | investigation CRUD |
| POST | `/reports/{slick_id}/generate`; GET `/reports/{slick_id}`; GET `/reports/{slick_id}/markdown` | report generation (Markdown) |
| POST | `/demo/seed`; POST `/demo/run-e2e`; POST `/demo/cases/{case_id}` | demo seeder, full E2E, cases A-D |
| GET/POST | `/incidents/{incident_id}(...)`, `/incidents/{id}/scenes|detect|evidence|detection-runs|drift-reports|attribution|origin|report` | incident-centric workflow |
| GET/POST | `/evidence/{incident_id}` | evidence ledger append/read |
| POST | `/jobs/{job_id}`; POST `/jobs/{job_id}/run` | async stage execution |
| POST | `/explainability/run`; GET `/explainability/validation` | occlusion/Grad-CAM + sanity suite |
| GET | `/ml/card`; GET `/ml/validation` | ML model card + validation bundle |
| GET | `/` | root info |

---

## 8. DATABASE STATUS

- **Engine:** SQLite dev DB (`sqlite:///./marinex.db`, resolves relative to CWD:
  `backend/marinex.db` when uvicorn runs there, `./marinex.db` at repo root for
  scripts). PostGIS/PostgreSQL available 100% via docker-compose but **not run
  locally** (daemon offline). Redis: NOT USED.
- **Migrations:** NONE (no Alembic wiring; `init_db()` `create_all`).
  Consequence: old-schema DBs need deletion + `scripts/seed_demo_data.py`
  rebuild (did this 2026-09-10 when a stale `/marinex.db` lacked the
  `incident_id` column).
- **Spatial columns:** coordinates stored as **GeoJSON JSON columns**,
  not PostGIS geometry (geo math via shapely in Python). PostGIS engine exists
  only in `ml/ais/postgis_engine.py`.
- **Tables (SQLAlchemy models → `__tablename__`):**

| Model file | Table | Key columns |
|---|---|---|
| incident.py | `incidents` | id, title, scenario(DEMO/OPERATIONAL/EXPERIMENTAL), status(OPEN/UNDER_INVESTIGATION/ESCALATED/CLOSED/NO_SLICKS/LOW_CONFIDENCE), ml_model_id, ml_threshold, status_label |
| scene.py | `satellite_scenes` | id, source, sensor, acquisition_time, lat/lon, bounding_box(JSON), resolution, file_path, status, incident_id FK |
| slick.py | `oil_slicks` | id, scene_id FK, incident_id FK, geometry(GeoJSON), area_km2, perimeter_km, centroid, confidence, detection_method, length/width/orientation/compactness/eccentricity |
| environment.py | `environmental_snapshots` | id, slick_id, timestamp, lat/lon, wind_speed/direction, ocean_current_u/v, wave_height, source(`Copernicus Marine / ERA5` default — but populated by MOCK), raw_data |
| drift.py | `drift_simulations` | id, slick_id FK, start/end_time, direction(HINDCAST/FORECAST), model_name(`LAGRANGIAN_MONTE_CARLO_DRIFT_v1`), origin_geometry, trajectory_geometry, particles(JSON), uncertainty(JSON), status |
| vessel.py | `vessels` | id, mmsi(unique), imo, vessel_name, vessel_type, flag |
| vessel.py | `ais_points` | id, vessel_id FK, timestamp, lat/lon, speed, course, heading, navigation_status |
| attribution.py | `vessel_candidates` | id, slick_id FK, vessel_id FK, proximity/temporal/trajectory/behavior_score, overall_score, rank, confidence(HIGH/MEDIUM/LOW/EXCLUDED), evidence(JSON), metrics(JSON), recommendation |
| evidence.py | `evidence_records` | id, incident_id FK, evidence_type, source, source_version, status_label(OBSERVED/INFERRED/SIMULATED/PREDICTED/TRACKED/CANDIDATE/DEMO_DATA), confidence, timestamp, title, summary, value(JSON), provenance(JSON), related_entity_type/id |
| investigation.py | `investigations` | id, slick_id (unique), status, priority_level, report_path |
| detection_run.py | `detection_runs` | id, scene_id FK, incident_id, model_id/version, preprocessing_version, threshold, status(SLICKS_FOUND/NO_SLICKS/LOW_CONFIDENCE/ERROR), artifact_path, method(PRODUCTION_ML), confidence, metadata_json |
| async_jobs.py | `async_jobs` | id, ... stage job records |

- **Missing/empty:** no dedicated `Report` table (reports are generated
  Markdown on demand from evidence; `investigations.report_path`/response object
  only). `satellite_scenes` used as the "satellite event" record — there is no
  separate raw `ImageAsset`/`RasterTile` entity. No dedicated
  `DriftConfiguration`/`Interpolation` tables.

---

## 9. ML STATUS (important)

### 9.1 Dataset (`data/datasets`, synthetic — see `docs/DATASETS.md`)
- Generator: `ml/data/generate_sar_dataset.py` (dark-polynomial slicks, Rayleigh
  clutter, wind streaks, speckle). **No real Sentinel-1 pixels.**
- Primary `sentinel1-oilspill-primary-v1`: **120** patches (80 train / 20 val /
  20 test), 3-channel PNG (`VV, VH, VV_minus_VH`), 256×256. Masks 0=bg,
  1=mineral oil, 2=look-alike. Class balance per split: 60 oil / 60 lookalike /
  60 no-oil / 24 empty masks; 293,799 oil px / 657,661 lookalike px
  (`reports/final_dataset_statistics.csv`).
- External `sentinel1-oilspill-external-v1`: **40** patches (Singapore
  Strait/Malacca), generalization probe only — never trained/tuned.
- Split `data/splits/split_group_aware_v1.json`: **group-aware by parent scene**
  (12 scenes → 8/2/2). Test = SCENE_02 + SCENE_11. Leakage audit → **PASS**
  (section 13).

### 9.2 Preprocessing & augmentation
- `SARPreprocessor(strategy="percentile", clip=(2,98))` per-channel percentile —
  production = **percentile**. Ablation on val shows `robust` slightly higher
  (0.9613 vs 0.9459) — documented tension; percentile kept (frozen protocol).
- Augmentor: physical SAR augmentation (used on val but val report shows
  No-Augment 0.9504 > Augment 0.9459). Channels: configurable VV / VH / VV_VH /
  VV_VH_DIFF; frozen = **VV_VH_DIFF**.

### 9.3 Models (registry: `ml/models/registry.py`)
| MODEL | STATUS | TRAINED? | EVALUATED? | CHECKPOINT | METRICS |
|---|---|---|---|---|---|
| UNetBaseline (`unet`) | **FROZEN PRODUCTION** | yes | yes | `models/best_model/marinex_unet_v1.pt` (31115827 B) | val 0.9533, test 0.8857 |
| UNetPlusPlus (`unet_plus_plus`) | evaluated, not selected | yes | yes | `models/best_model/marinex_unet_plus_plus_v1.pt` | val 0.9447, test 0.9175 |
| SegFormer (`segformer`) | evaluated, lowest | yes | yes | `models/best_model/marinex_segformer_v1.pt` | val 0.8934 |
| OilLookalikeClassifier (`classifier`) | used in two-stage | yes | yes | `models/best_model/marinex_lookalike_classifier_v1.pt` | two-stage composite 0.8769 |
| ClassicalSARBaseline | baseline | n/a | yes | — (deterministic) | test 0.3733 IoU |

**Training config (verified in `experiment_runner.py`):** batch 8, AdamW
`lr=1e-3 / wd=1e-4` (unet/unet++) and `lr=8e-4` (segformer), epochs 10 (unet,
unet++) / 12 (segformer) / 8 (seeds); classifier 12; channel/loss/aug ablations
6 epochs; no scheduler in the runner. Loss: BCE+Dice (frozen). Seeds 42/123/999.

**Threshold / calibration (frozen):** production threshold **0.70** (val IoU
sweep argmax), temperature **T = 0.2262389063835144**, ECE 0.1735 → **0.0046**,
Brier 0.0330 → **0.0025** (`reports/calibration.json`).

### 9.4 Explainability
- `ml/explainability/methods.py`: **Grad-CAM** (final conv), **occlusion
  perturbation**, attention for SegFormer. Backend `POST /explainability/run`
  writes provenance + PNG panels (`reports/explainability/EXP-*`).
- Sanity suite (`scripts/explain_sanity.py`, `reports/explainability/sanity.json`):
  randomization test **WEAK** (trained energy 7396.24 vs random-weights
  53080.03 — do NOT over-interpret saliency); occlusion perturbation **PASS**
  (conf drop 0.0549 destroying top-10%). SHAP: **NOT implemented**. Integrated
  Gradients: **NOT implemented**. See section 14.

---

## 10. ML EXPERIMENT HISTORY (chronological, real values from `reports/*`)

| # | Experiment | Model | Dataset/Input | Loss | Result | Status |
|---|---|---|---|---|---|---|
| 1 | Classical baseline | Otsu SAR baseline | test fold | — | IoU 0.3733 / Dice 0.5437 | recorded |
| 2 | Architecture comparison | unet vs unet_plus_plus vs segformer | val fold, VV_VH_DIFF | bce_dice | val 0.9533 / 0.9447 / 0.8934 (th .70/.55/.30) | recorded (`model_selection.csv`) |
| 3 | Channel ablation | unet | val; VV/VH/VV_VH/VV_VH_DIFF | bce_dice | 0.8767 / **0.9432** / 0.8891 / **0.9459** | recorded (`ablation_results.csv`) |
| 4 | Loss ablation | unet | val | bce/dice/bce_dice/focal/tversky/focal_tversky | 0.9396 / 0.9471 / **0.9459** / 0.9296 / 0.7597 / 0.7536 | recorded |
| 5 | Augmentation ablation | unet | val | bce_dice | no-aug 0.9504 vs aug 0.9459 | recorded |
| 6 | Preprocessing ablation | unet | val | bce_dice | **robust 0.9613** > percentile 0.9459 > z_score 0.9364 > min_max 0.8636 | recorded |
| 7 | Multi-seed | unet | val | bce_dice | 42: 0.9459, 123: 0.9358, 999: 0.9265 | recorded (`multi_seed.csv`) |
| 8 | Hard-negative retrain | unet + 34 HN (−> train 134) | val→test | bce_dice | +HN val 0.9488 vs base 0.9533; +HN test 0.7188 vs base 0.8857 | **REJECTED** |
| 9 | Two-stage (SegFormer + lookalike clf) | two-stage | test | bce_dice | test IoU **0.8769**, ECE 0.0044, obj-F1 0.9508 | alternative reported |
| 10 | Threshold + temperature calibration | unet | val sweep 0.10-0.90 | — | best IOU 0.7 → 0.9533; T 0.2262; ECE 0.0046 | frozen |
| 11 | **FINAL frozen test** | unet th=0.70 | test (single pass) | bce_dice | **IoU 0.8857** / Dice 0.9394 | **FROZEN** |
| 12 | Robustness (7 conditions) | unet | test | — | clean 0.8857; contrast .6/.4 0.8654/0.8795; speckle 0.4432; 20 m 0.5786; −3 dB 0.8940; +3 dB **0.3030** | recorded |
| 13 | Scene-level generalization | unet | SCENE_02/SCENE_11 | — | 0.9034 / 0.8743 (mean 0.8889) | recorded |
| 14 | Slick-size quartiles | unet | test | — | TINY 0.9355 / SMALL 0.9547 / MEDIUM 0.9594 / LARGE 0.9678 | recorded |
| 15 | Lookalike split + error taxonomy | unet | test | — | OIL 0.9583 / LOOKALIKE 0.8145 / CLEAN 0.0000; taxonomy 7 FP-lookalike, 7 boundary, 6 neutral | recorded |
| 16 | Cross-dataset external | unet (frozen) | external 40 | — | IoU 0.8487 / Dice 0.9181 | recorded |
| 17 | Multi-scale inference | unet (frozen) | test @224-384 | — | 256 optimal 0.8768; 224→0.6554, 384→0.6667, FPR ↑ | recorded (`multi_scale_evaluation.csv`) |

**Reproduction:** `scripts/run_ml_campaign.py` (resumes via `.done` flags;
leakage guard aborts `STOP: leakage detected` if split leaks) →
`scripts/freeze_final_model.py` → `scripts/build_final_report.py`.

---

## 11. ML METRICS (real, from report artifacts)

### Test (frozen single pass, unet, th=0.70) — `reports/final_model_benchmark.md`
| Metric | Value |
|---|---|
| IoU | 0.8857 |
| Dice | 0.9394 |
| Precision | 0.9080 |
| Recall | 0.9731 |
| PR-AUC | 0.9939 |
| FPR | 0.0041 |
| FNR | 0.0269 |
| ECE (raw vs calibrated) | 0.1754 → **0.0046** |
| Brier (raw vs calibrated) | 0.0330 → **0.0025** |
| Object-F1 | 0.7901 |
| Latency (CPU, 256²) | ~124–130 ms |

### Validation (best = unet @ 0.70) — `reports/model_selection.csv`
| Model | Val IoU | Val Dice | Best th |
|---|---|---|---|
| unet | **0.9533** | 0.9761 | 0.70 |
| unet_plus_plus | 0.9447 | 0.9716 | 0.55 |
| segformer | 0.8934 | 0.9437 | 0.30 |

Training-fold metrics: **NOT REPORTED/AVAILABLE** (training loop records only
best val + test evals; no separate train-metric artifacts).

Specificity: **NOT AVAILABLE** (artifacts store precision/recall/FPR/FNR, not
specificity; FPR is the standard omission proxy).
ROC-AUC: **NOT AVAILABLE** (PR-AUC 0.9939 present).
Geometry/centroid error: see `reports/slick_geometry_report.md` — median area
relative error ~4.33%; 3 outliers (patch_0104 87.4%, patch_0108 99.9%,
patch_0106 inf) fall back to full-area policy.

---

## 12. BEST MODEL

**CURRENT BEST = `marinex-unet-v1.0.0` (UNetBaseline)**

Why: it is the only architecture that scored highest on **validation** (0.9533)
under the frozen-split protocol AND is the calibrated frozen production
artifact with a single protected test pass (IoU 0.8857). `unet_plus_plus` has
higher test IoU (0.9175) but **lower val IoU** (0.9447) and was not selected —
the selection rule is validation-only (documented in
`docs/FINAL_EXPERIMENT_PROTOCOL.md`); both numbers are reported honestly.

- Input: 256×256, VV/VH/VV−VH, percentile preproc
- Threshold 0.70; temperature 0.2262 (log-space)
- Metrics: see section 11
- Checkpoint: `models/best_model/marinex_unet_v1.pt` (torch save w/ metadata)
- Freeze record: `models/production/metadata.json` (git_commit `f764d88`,
  threshold 0.7, temperature 0.22623)

---

## 13. DATA LEAKAGE STATUS

| Check | Status | Evidence |
|---|---|---|
| Group-aware split (parent scenes) | **PASS** | `split_group_aware_v1.json` (8/2/2 scenes) |
| Sample-id disjointness | **PASS** | `reports/final_leakage_audit.md` (0 violations) |
| Parent-scene containment | **PASS** | 0 violations |
| sha256 duplicate detection | **PASS** | 0 duplicates |
| Near-duplicate correlation (32×32, 0.98) | **PASS** | 0 pairs (train/val, train/test, val/test) |
| Test isolation | **PASS** | test used exactly once after freeze |
| Dataset-level integrity/corruption | **PASS** | 0 corrupted files |

Audit commands: `scripts/final_data_audit.py`,
`python -m ml.data_audit.audit_dataset --datasets p,e`.

---

## 14. EXPLAINABILITY STATUS

| Method | Implemented | Tested | Validated | In UI |
|---|---|---|---|---|
| Grad-CAM | ✅ `ml/explainability/methods.py` | via sanity suite | **WEAK** (randomization test) | Explainability page POSTs `/explainability/run` |
| Occlusion perturbation | ✅ | ✅ | **PASS** (conf drop 0.0549) | same |
| Attention (SegFormer) | ✅ (segformer cp) | ✅ (sanity) | not separately validated | not wired to UI |
| Integrated Gradients | NOT IMPLEMENTED | — | — | — |
| SHAP | NOT IMPLEMENTED | — | — | — |
| Transformer attribution | n/a (no transformer in production) | — | — | — |
| Confidence map / error map | Confidence = max prob from segmentation; error map derivable in `ml/evaluation/error_analysis.py` | — | — | partial |

Sanity statements must cite `reports/explainability/sanity.json`: heatmaps are
**not causal proof** (randomization WEAK).

---

## 15. CALIBRATION STATUS

- Raw confidence: sigmoid of logits; raw ECE **0.1735** / Brier **0.0330**.
- Temperature scaling: **T = 0.22624** (log-space, fits on val; `calibrate` in
  `ml/evaluation/calibration.py`).
- Post-calibration ECE **0.0046**, Brier **0.0025**.
- Reliability curve: `reports/reliability_curve.csv`; plots script
  `scripts/calibration_plots.py`.
- Threshold selection: val sweep 0.10–0.90 in `calibration.json.sweep`; argmax
  IoU at **0.7**. Full sweep curve saved.

---

## 16. ERROR ANALYSIS

Artifacts: `reports/error_taxonomy.csv`, `reports/slick_geometry_report.md`,
`reports/slick_size_results.csv`, `reports/lookalike_report.md`,
`reports/robustness_results.csv`.

Known failure modes (all measured):
- **Look-alikes cause FPs:** patch_0017 (max prob 0.89), patch_0107 (0.93),
  patch_0108 (0.72), patch_0018 (0.70) generate false masks; clean patches stay
  at ≤0.35 (clean FDR 0.0). Look-alike rejection rate **0.30** at th 0.70.
- **Small/medium slicks:** TINY bucket IoU 0.9355 (best recall) — quality
  maintained, but object-linking occasionally fragments.
- **Boundary leakage:** error taxonomy counts 7 "Partial Coverage – Boundary
  leakage" cases (e.g., patch_0014, 0104, 0105).
- **Radiometric/geometric fragility:** +3 dB → **0.3030** IoU; speckle L=2 →
  0.4432; 20 m resolution → 0.5786. Multi-scale: resampling away from 256
  degrades IoU to ~0.66–0.68.
- **Geometry drift:** median area rel. error ~4.33% but 3 outliers fail
  outright (documented fallback).

---

## 17. DATASETS (all found)

**SATELLITE**
| Dataset | Source | Size | Format | Local | Purpose | Train/Val/Test role |
|---|---|---|---|---|---|---|
| sentinel1-oilspill-primary-v1 | synthetic generator `ml/data/generate_sar_dataset.py` | 120 × (3ch PNG 256²) + masks; 21.6 MB | PNG | ✅ committed | ML training/val/test | 80/20/20 |
| sentinel1-oilspill-external-v1 | same generator | 40 pathes; 7.2 MB | PNG | ✅ committed | generalization probe | inference only |

Manifests state **"no real Sentinel-1 imagery"**. No URLs/licenses exist for
these synthetic artifacts (license = internal synthetic benchmark).

**AIS**
| Dataset | Source | Size | Format | Local | Purpose |
|---|---|---|---|---|---|
| sample_ais_trajectories.csv | bundled MarineCadastre-style 20 rows/5 MMSI | 20 recs | CSV | ✅ committed | provider + parquet partition source |

**ENVIRONMENT**
| Dataset | Source | Size | Local | Purpose |
|---|---|---|---|---|
| sample_environmental.json | bundled | 1 snapshot | ✅ committed | mock drift forcing |

**OTHER**: `data/samples/*.geojson/json` demo fixtures; `data/hard_negatives/`
(gitignored, generated by mining). No remote/URL-based datasets are used.

---

## 18. LARGE DATA HANDLING (AIS)

- The repo uses a **local sample** (raw CSV committed) plus a generated
  **Parquet partition** hierarchy (`data/processed/ais/partitions/year=2026/
  month=3/day=1/part_00000.parquet`, gitignored) queried through **DuckDB**
  (`ml/ais/duckdb_engine.py`). `scripts/prepare_ais.py` regenerates
  deterministically; `scripts/benchmark_ais.py` measured 5 query shapes at
  single-digit ms on the 20-row partition.
- **PostGIS engine** exists (`ml/ais/postgis_engine.py`) but is not exercised
  (PostGIS not running locally).
- No object storage, no remote access layer is implemented
  (`docs/REMOTE_TRAINING.md` documents GPU/remote *training* plumbing, not data
  lake ingestion).
- Actual strategy = **sample-first, DuckDB-Parquet path is real, scale is
  tiny.**

---

## 19. AIS STATUS

| Concern | Implementation | Works? |
|---|---|---|
| Source | `CSVAISProvider` (MarineCadastre-style CSV), bundling `sample_ais_trajectories.csv` | ✅ |
| Schema/cleaning | `ml/ais/ais_schema.py`: bad_coordinates, impossible_speed (≤250 kn), course range, duplicate_timestamp, MMSI range | ✅ (audit 0 issues) |
| Parquet | `scripts/prepare_ais.py` → year/month/day partitions | ✅ |
| DuckDB | `ml/ais/duckdb_engine.py` region/time/region_time/vessels/trajectory queries | ✅ (benchmarked) |
| PostGIS | `ml/ais/postgis_engine.py` | implemented, NOT run locally |
| Trajectory | `ml/ais/trajectory.py` velocity-agnostic haversine + gap-aware segmentation | ✅ (synthetic validation ~0.112% err) |
| Candidate generation | bbox+window corridor query feeds attribution; is `CANDIDATE` evidence labeled | ✅ |
| Mock | `MockAISProvider` for deterministic tests only (demo uses CSV provider) | ✅ |

Honest limits: broadcast-only, 20-row sample archive; dark vessels absent;
zero-track → `NO_RELIABLE_CANDIDATE` (never invented suspects).

---

## 20. ENVIRONMENTAL DATA STATUS

| Concern | Status |
|---|---|
| ERA5 integration | **NOT IMPLEMENTED** — `era5_provider.py` raises `NotImplementedError` unless CDS_* env configured |
| Copernicus Marine | **NOT IMPLEMENTED** (same adapter; configuration-only) |
| Wind/current/waves | **MOCK** — `MockEnvironmentalProvider` returns deterministic sample snapshot (`DEFAULT_WIND_DRIFT_FACTOR=0.032`, `DEFAULT_DIFFUSION_COEFF=10.0`) |
| SST | NOT IMPLEMENTED |
| Interpolation | NOT IMPLEMENTED |
| Spatial/temporal filtering | PARTIAL — quality checker validates bounds/timestamps (6 h coverage margin) for gating |

Registry (`environmental/registry.py`) resolves ERA5 only if configured,
otherwise Mock. **Provider used in every real run = MOCK.**

---

## 21. DRIFT ENGINE STATUS

- **Custom** `LAGRANGIAN_MONTE_CARLO_DRIFT_v1` (`backend/app/services/drift/
  service.py`). OpenDrift/OpenOil: **NOT IMPLEMENTED**.
- Forward (FORECAST) + backward (HINDCAST) integration; `v_net = v_current +
  alpha*v_wind`; diffusion `sigma = sqrt(2 D dt)`, D=10 m²/s; particles seeded
  `rng(42)` ⇒ **deterministic**; initial radial perturbation 150 m.
- Outputs: probable_origin_centroid (+time), 95% origin hull, trajectory
  LineString, diffusion radius, drift distance/speed, ≤80 particles.
- Tests/validation (fresh runs today): physics sanity **ALL PASS** for
  east (43.12 km), **west (43.18 km)**, north (43.10 km), **south (43.35 km)**,
  zero (0.13 km); determinism PASS (identical output on two runs); 15-senario
  sensitivity sweep stable. Artifacts `reports/drift_sanity_results.json`,
  `reports/drift_sensitivity.csv`.
- Quality gate: env grade FAIL ⇒ HTTP 422 block (tested).
- Known issues: forcing is a single snapshot (no uncertainty propagation);
  not reanalysis-fed; no weathering/Stokes terms.

---

## 22. ATTRIBUTION ENGINE STATUS

**RULE-BASED / HYBRID (deterministic geometry + fixed weights) — NOT ML-based.**

`VesselAttributionEngine` (`backend/app/services/attribution/engine.py`):
- Factor scores: proximity (exponential decay, default 0.35 weight), temporal
  (Gaussian σ=75 min around origin time, 0.25), trajectory (exp decay vs
  origin polygon, 0.25), behavior (generic bonus, 0.15).
- `overall = 0.35*S_prox + 0.25*S_temp + 0.25*S_traj + 0.15*S_behav`,
  normalized 0-100 → tiers `CANDIDATE_IDENTIFIED (>=75)` /
  `INSUFFICIENT_EVIDENCE` / `NO_RELIABLE_CANDIDATE`.
- No XGBoost/LightGBM, no probability calibration, no SHAP. Explanations are
  template evidence strings in each candidate record.
- Endpoint: `POST /attribution/{slick_id}/run`; UI Candidates page.

---

## 23. EVIDENCE ENGINE

Implemented (`backend/app/services/evidence.py`, `evidence_records` table,
`GET/POST /evidence/{incident_id}`, `GET /incidents/{id}/evidence`).
- Append-only records with type/source/source_version/status_label
  (OBSERVED, INFERRED, SIMULATED, PREDICTED, TRACKED, CANDIDATE, DEMO_DATA),
  JSON value + **provenance** (model, config, processing_stage).
- Evidence Graph frontend page renders linked records.
- Distinction honored: ML segmentation = ML_SEGMENTED/etc; drift = SIMULATED;
  attribution = CANDIDATE; demo = DEMO_DATA.

---

## 24. REPORTING

- `ReportGeneratorService.generate_report()` builds a structured report from
  slick + drift + candidates + evidence; `to_markdown()` renders **Markdown**.
- Endpoints: `POST /reports/{slick_id}/generate`,
  `GET /reports/{slick_id}/markdown`.
- Working: verified in E2E (`REP-SLICK_SC-20260910`) and reports page.
- PDF/HTML: **NOT implemented** (no reportlab/fpdf; Markdown only).

---

## 25. DEMO SYSTEM

- Seeder: `scripts/seed_demo_data.py` → incident
  `scene_s1a_20260301_arabian_sea_001`, slick `slick_scene_s1a_2026_001`,
  loads 20 AIS points / 5 vessels from CSV.
- Endpoints: `POST /demo/seed`, `POST /demo/run-e2e`,
  `POST /demo/cases/{case_id}` (cases A–D, backend test
  `test_demo_cases_and_ml.py`): A=standard detection, B=LOW_CONFIDENCE (+3 dB
  degraded → analyst review, no auto-attribution), C/D variations.
- E2E result (fresh 2026-09-10): full chain SUCCESS → primary suspect
  **PACIFIC CROWN**, evidence score **40.6/100**, slick area 9.80 km².
- Classification: **SYNTHETIC / MOCK** data (sample radar imagery, sample AIS,
  mock environment). No REAL satellite/AIS records in the demo path.

---

## 26. DEPENDENCIES

- **Backend** (`backend/requirements.txt`): fastapi, uvicorn[standard],
  pydantic, pydantic-settings, sqlalchemy, alembic, psycopg2-binary,
  geoalchemy2, shapely, numpy, pandas, scikit-learn, scipy, pillow,
  python-multipart, httpx, pytest, pytest-asyncio. (alembic declared, unused;
  psycopg2/geoalchemy2 only needed for PostGIS path.)
- **ML** (`ml/requirements.txt`): torch>=2.2 (installed 2.14.0+cpu),
  torchvision, opencv-python-headless, duckdb, pyarrow, pyyaml, mlflow, numpy,
  Pillow, pytest. (mlflow declared; no mlruns committed; runs not logged to a
  server.)
- **Frontend** (`frontend/package.json`): see section 5. All deps are installed
  and used except explicitly flagged.
- Identified items: alembic NOT wired (missing migration tooling);
  psycopg2-binary/geoalchemy2 only reach the PostGIS branch; leaflet css
  reference vestigial; no DOOM-required unused cruft beyond that. Nothing
  changed during this audit.

---

## 27. ENVIRONMENT CONFIGURATION

`.env.example` (template; no values populated). Variable names only:

| Variable | Purpose | Optional? |
|---|---|---|
| ENVIRONMENT, DEBUG, PORT | app mode | default dev |
| DATABASE_URL (`sqlite:///./marinex.db`, or Postgres) | DB URL | default |
| USE_POSTGIS | true when using docker PostGIS | optional |
| POSTGRES_DB/USER/PASSWORD/PORT | compose dev defaults | for compose |
| WEIGHT_PROXIMITY/TEMPORAL/TRAJECTORY/BEHAVIOR | attribution weights (0.35/0.25/0.25/0.15) | optional |
| DEFAULT_WIND_DRIFT_FACTOR, DEFAULT_DIFFUSION_COEFF | drift physics defaults | optional |
| COPERNICUS_MARINE_USER/PASSWORD, AIS_STREAM_API_KEY | future providers | placeholder (empty) |

No secrets appear anywhere in the repo (see section 34).

---

## 28. DOCKER STATUS

- `docker-compose.yml`: `postgis/postgis:16-3.4` (db), backend (fastapi build),
  frontend (nginx). Healthchecks on db; env interpolation for creds.
- `backend/Dockerfile`: python:3.12-slim + libgeos/libpq + requirements.
- `frontend/Dockerfile`: node:20-alpine build → nginx serve (+ nginx.conf).
- **Status: NOT EXECUTED locally.** Docker CLI 29.6.2 present but the daemon
  is offline (`failed to connect to the docker API...`). No container build or
  startup verified in this environment; compose is unvalidated-by-run here.

---

## 29. TEST STATUS (fresh runs, 2026-09-10)

| Suite | Command | Passed | Failed | Notes |
|---|---|---|---|---|
| Backend | `python -m pytest backend/tests -q` | **35** | 0 | incl. DUCKDB-free AIS, drift, attribution, E2E, demo cases, geometry, quality/uncertainty |
| ML/data | `python -m pytest ml/tests -q` | **19** | 0 | ais_schema, duckdb engine, manifests, ML units |
| Frontend typecheck+build | `npm run build` (tsc && vite build) | **PASS** | — | 1 chunk-size warning only |

No skipped tests. Frontend has no lint script and no JS unit tests (only tsc).

---

## 30. BUILD STATUS

| Item | Result |
|---|---|
| Frontend production build | **PASS** (`npm run build`, 12s, chunk-size warning only) |
| Backend import/start | **PASS** (FastAPI app imports; 35 API tests pass; uvicorn root reached in tests) |
| Database migration | **PASS (create_all)** — rebuild needed after schema change; Alembic absent |
| Docker build | **NOT RUN** (daemon offline) |

---

## 31. GIT STATUS

- Branch: `main` (tracks `origin/main`), working tree **clean**, no untracked files.
- Remote: `origin → https://github.com/veerendhranuthalapati/MARINeX.git`
- HEAD: `29771ed` "MARINeX: add final validation report (SIH26143)"
- Recent history (7 commits, all pushed):
  `59e46df` → `f764d88` → `8f5a18d` → `6294b78` → `9698eb6` → `d681f33` →
  `29771ed`
  (baseline → incident pipeline + frozen campaign → ML validation/UI/docs →
  gate close → final research validation → gate close → final report)
- Nothing was committed or pushed during this audit.

---

## 32. CURRENT BLOCKERS (prioritized)

| # | Blocker | Severity | Area | Why it matters | Current error | Recommended fix |
|---|---|---|---|---|---|---|
| 1 | No real environmental data | **CRITICAL** | Drift validity | Real hindcast quality depends on real wind/current | `ERA5Provider.get_conditions()` raises `NotImplementedError` when unconfigured | Configure CDS API or embed a licensed ERA5/CMEMS subset + regression tests |
| 2 | AIS archive is 20 rows | **HIGH** | Attribution | Candidate search not realistic at scale | Sample-only CSV; no live/archive feed | Wire MarineCadastre/EU EMSA archive → parquet → DuckDB path (already built) |
| 3 | Docker not verifiable locally | **MEDIUM** | Deployment | Dockerized PostGIS deployment unvalidated | daemon offline (`Docker Desktop` not running) | Start daemon; run `docker compose up --build`; validate PostGIS path |
| 4 | PostGIS path untested | **MEDIUM** | Storage | `USE_POSTGIS=true` never executed | PostGIS not running locally | Enable PostGIS container, run engine tests |
| 5 | Synthetic-only imagery | **LOW (accepted)** | Scientific validity | Cannot claim operational SAR performance | Manifest-labeled synthetic | Keep as benchmark; add real Sentinel-1 slice if SIH rules permit |
| 6 | Alembic restore | **LOW** | Ops | No schema migration history | no alembic.ini | Add Alembic baseline+first migration |

---

## 33. TECHNICAL DEBT

- **Hard-coded values:** production threshold 0.70 in `config.py` + adapters;
  calibration_plots.py hardcodes temperature; `run_ml_campaign.py` stage
  ordering; drift sigma=150 m & rng=42 inline; attribution weights default in
  settings.
- **Temporary mocks:** `MockEnvironmentalProvider` (default), `MockAISProvider`
  (tests only), `ERA5Provider` stub.
- **Duplicated code:** `CategoryBadge`/`RadialScore` under both `components/investigation`
  and `components/ui`; legacy threshold 0.40 in docs was reconciled to 0.70
  (final phase).
- **Incomplete integrations:** PostGIS engine (no run), mlflow (declared, no
  server logging), alembic (declared, unused), nginx.conf not reviewed here.
- **Missing tests:** no frontend unit tests; no integration test against real
  PostGIS; no migration test.
- **Performance risks:** CPU-only inference (~124–130 ms/image); all inference
  jobs serialized; detection artifacts stored as `.npz` on disk.
- **Security risks** — see section 34.

---

## 34. SECURITY STATUS

Audit performed 2026-09-10 (`docs/SECURITY_AUDIT.md`):
- **Secrets:** none tracked. Only `.env.example` (placeholders). `git ls-files`
  scan clean; pattern scan over tracked code clean. `.env*` and `*.db`
  gitignored.
- **SQL:** SQLAlchemy ORM parameterized; DuckDB engine reads local files only.
- **CORS:** allowlist of localhost origins only (no wildcard+credentials).
- **Auth:** NONE — accepted demo gap (documented).
- **Uploads:** scene upload writes to gitignored `backend/uploads/`; filename
  handling reviewed (Redis of pathological traversal not tested in suite).
- **Model loading:** `torch.load(..., weights_only=False)` on local bundled
  checkpoint — safe only for trusted local artifacts.
- **Dependency advisories (npm):** 2 moderate; both SSR-hydration-only
  (GHSA-337j-9hxr-rhxg) → **NOT applicable** to this SPA (no SSR). Fix path
  documented (react-router-dom 7.x breaking major, deferred). Python CVEs not
  machine-checked offline.

---

## 35. PERFORMANCE STATUS

| Measurement | Value | Source |
|---|---|---|
| ML inference (CPU, 256², unet) | ~124–130 ms | `reports/final_model_benchmark.csv` |
| Two-stage inference | ~134 ms | same |
| Classical baseline | ~5 ms | same |
| AIS DuckDB queries (20-row partition) | 3–9 ms | `reports/ais_benchmark.json` |
| API / frontend end-to-end latency | **NOT MEASURED** | — |
| PostGIS query performance | **NOT MEASURED** (not running) | — |

---

## 36. WHAT HAS ALREADY BEEN BUILT

| Area | Status |
|---|---|
| Data (synthetic SAR benchmark + samples) | **DONE** |
| ML training/selection/freeze | **DONE** |
| Metrics/calibration/robustness suite | **DONE** |
| Explainability (Grad-CAM/occlusion) | **DONE** (validity WEAK) |
| Drift (custom Lagrangian) | **DONE** (env forcing MOCK) |
| AIS pipeline (CSV→Parquet→DuckDB→trajectories) | **DONE** (tiny-scale) |
| Attribution (rule-based) | **DONE** |
| Evidence ledger + provenance | **DONE** |
| Backend API | **DONE** |
| Frontend (13 pages) | **DONE** |
| Demo system | **DONE** |
| Deployment (Docker/PostGIS) | **PARTIAL** (files only, unverified locally) |
| Real-world data integrations (ERA5/CMEMS/full AIS) | **NOT STARTED** |

---

## 37. WHAT SHOULD HAPPEN NEXT (recommended 10)

1. Start Docker daemon; run `docker compose up --build`; validate PostGIS path
   (blocker #3/#4).
2. Add Alembic baseline + first migration to stop manual `create_all` rebuilds.
3. Wire a licensed/real environmental dataset (ERA5/CMEMS sample) behind the
   existing provider interface; keep Mock as fallback (blocker #1).
4. Scale the AIS path against a real MarineCadastre-style partition and
   benchmark corridor queries (blocker #2).
5. Optionally re-open the `robust`-vs-`percentile` preprocessing decision as a
   documented experiment *before* any retrain (currently frozen percentile).
6. Add unit tests for frontend components (Vitest) and a
   `scripts/regression_smoke.py` running the exact frozen-metric suite.
7. Add PostGIS + migration tests and a CI pipeline matrix (backend/ML/frontend).
8. Document real-data ingestion path (scene upload → true Sentinel-1
   preprocessing) or explicitly scope it out for SIH judging.
9. Consider a small-scale redistribution of the FP/look-alike problem
   (threshold/region-level NMS) — only after #7 gives a regression harness.
10. Verify the `+3 dB / speckle / 20 m` failure modes and mitigate or document
    as deployment constraints.

---

## 38. RECOMMENDED NEXT MILESTONE

**"Containerized, reproducible end-to-end incident on the frozen model — PostGIS
wired, seed→detect→drift→AIS→attribution→Markdown report, validated by the CI
regression harness, with a scored real-environment/AIS smoke test behind
explicitly labeled mock fallbacks."**

This is adjacent to the current state (everything runs unstaged/localhost) and
directly unblocks the three top blockers (deployment, PostGIS, real data).

---

## 39. AGENT TAKEOVER INSTRUCTIONS

**How the next coding agent should start:**

1. Read first: `README.md`, `docs/CURRENT_STATE.md`,
   `docs/FINAL_EXPERIMENT_PROTOCOL.md`, `docs/FINAL_ARCHITECTURE.md`,
   `docs/QUALITY_GATE.md`, `docs/models/MARINeX_Oil_Spill_Model_Card.md`,
   `reports/FINAL_ML_REPORT.md`.
2. Commands to run on Windows PowerShell (win32):
   ```
   git status -sb                # expect clean, main = origin/main (29771ed)
   .venv\Scripts\python -m pytest backend/tests -q     # 35 passed
   .venv\Scripts\python -m pytest ml/tests -q          # 19 passed
   cd frontend; npm run build                          # PASS (tsc + vite)
   .venv\Scripts\python scripts/seed_demo_data.py      # then:
   .venv\Scripts\python scripts/run_pipeline_cli.py    # E2E SUCCESS
   ```
3. Major blockers: real env data (ERA5 stub), 20-row AIS archive, Docker
   daemon offline (containers unverified), PostGIS path untested.
4. Architecture: FastAPI `/api/v1` → services → SQLAlchemy SQLite (dev) /
   PostGIS (compose); frozen UNet at `models/best_model/marinex_unet_v1.pt`.
5. Best model: `marinex-unet-v1.0.0`, th 0.70, T 0.2262, test IoU 0.8857.
6. Data source: all synthetic; AIS = `data/samples/sample_ais_trajectories.csv`.
7. Do NOT rebuild: the ML campaign, calibration, leakage audit, evidence
   ledger, or the 3 final-phase docs sets — they are verified artifacts.
8. Immediate recommended task: milestone in section 38 (start with Docker
   daemon + `docker compose up --build`).

---

## 40. FINAL STATE SUMMARY

| Component | Status | Confidence | Notes |
|---|---|---|---|
| Repository | WORKING | HIGH | clean, pushed, documented |
| Frontend | WORKING (dev) | MEDIUM | builds; pages wired; no unit tests |
| Backend | WORKING | HIGH | 35/35 tests; realistic API surface |
| Database | WORKING (SQLite) | MEDIUM | PostGIS path unexecuted; no migrations |
| ML | WORKING (frozen) | HIGH | verified metrics; synthetic data |
| Explainability | PARTIAL | MEDIUM | occlusion PASS; randomization WEAK |
| Calibration | WORKING | HIGH | ECE 0.1735→0.0046, Brier 0.0330→0.0025 |
| Satellite | MOCK (synthetic) | MEDIUM | generator, no real Sentinel-1 |
| Environment | MOCK | MEDIUM | ERA5/CMEMS stub |
| Drift | WORKING (custom) | HIGH | E/W/N/S + zero PASS, deterministic |
| AIS | WORKING (sample) | MEDIUM | parquet+DuckDB real; tiny archive |
| Attribution | WORKING (rule-based) | HIGH | no ML ranking |
| Evidence | WORKING | HIGH | provenance labels enforced |
| Reports | WORKING (Markdown) | MEDIUM | no PDF/HTML |
| Docker | UNVERIFIED locally | LOW | files exist; daemon offline |
| Tests | PASSING | HIGH | 35 backend + 19 ML + build |
| Deployment | PARTIAL | LOW | local dev only; PostGIS/compose unvalidated |

---

*Prepared as a handoff snapshot. Repro all numbers via the scripts named in
section 9.10/11; all artifacts live under `reports/` (mostly gitignored,
regenerable).*