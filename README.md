# MARINeX — Satellite Oil Spill Detection & AIS Vessel Attribution Platform

[![SIH 2026](https://img.shields.io/badge/SIH-2026--SIH26143-0077b6.svg)](https://www.sih.gov.in/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20TS-61dafb.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Smart India Hackathon 2026 — Problem Statement SIH26143**  
> *"Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill."*

---

## 1. Problem Overview

Illegal operational oil discharges and accidental bunker spills in coastal and offshore shipping corridors cause severe ecological and economic damage. In the Indian Exclusive Economic Zone (EEZ), thousands of tankers and cargo vessels transit daily. Identifying delinquent polluters is challenging because:
- Satellite imagery captures oil slicks hours after the discharge occurred.
- Ocean surface currents and winds rapidly transport and disperse the slick far from its origin.
- Traditional AIS tracking yields hundreds of candidate ships along dense maritime lanes.
- Enforcement agencies (Indian Coast Guard, DG Shipping, Port State Control) require **defensible, explainable forensic evidence** before initiating vessel boardings or legal action.

**MARINeX** solves this with a coupled multi-stage pipeline:
1. **SAR Satellite Ingestion & Segmentation**: Detects dark radar backscatter suppression from capillary wave dampening.
2. **Morphometric Slick Characterization**: Computes surface area, perimeter, orientation, and compactness.
3. **Lagrangian Drift Hindcasting**: Backward-in-time advection and turbulent diffusion modeling using ocean currents and wind leeway forcing to reconstruct the **probable origin region and 95% uncertainty envelope**.
4. **AIS Corridor Correlation**: Filters and traces vessel trajectories in the spatio-temporal search window.
5. **Explainable Attribution Engine**: Computes 4 independent factor scores (Proximity, Temporal, Trajectory, Behavior) and outputs natural-language forensic audit evidence.
6. **Command Dashboard & Incident Dossier**: Geospatial visualization and automated Port State Control report generation.

---

## 2. Architecture Diagram

```mermaid
graph TD
    A[Sentinel-1 C-SAR / Sentinel-2 Scene] --> B[Oil Spill Detector]
    B -->|Classical Baseline / Deep Learning| C[Slick Characterization Engine]
    C -->|Area, Perimeter, Centroid, Bbox| D[OilSlick Database Entity]
    
    D --> E[Environmental Data Service]
    E -->|Surface Currents & 10m Winds| F[Lagrangian Drift Hindcasting]
    F -->|Negative Time Integration| G[Probable Origin Region & Uncertainty Polygon]
    
    G --> H[AIS Provider / Spatial Filter]
    H -->|Historical CSV / Live Stream| I[Vessel Trajectory Tracks]
    
    G --> J[Vessel Attribution Engine]
    I --> J
    J -->|Proximity, Temporal, Trajectory, Behavior| K[Ranked Candidate Polluters & Evidence Dossier]
    
    D --> L[Geospatial Intelligence Dashboard]
    G --> L
    K --> L
    L --> M[PSC Forensic Investigation Report]
```

---

## 3. Monorepo Structure

```text
MARINeX/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application, CORS, lifespan & static mounting
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic BaseSettings, paths, scoring weights
│   │   │   ├── database.py            # SQLAlchemy engine, session maker (SQLite / PostGIS)
│   │   │   └── logging.py             # Structured logger
│   │   ├── models/                    # Domain models: Scene, Slick, Environment, Drift, Vessel, Candidate, Investigation
│   │   ├── schemas/                   # Pydantic v2 validation schemas & GeoJSON types
│   │   ├── repositories/              # Clean DB data access layer
│   │   ├── services/
│   │   │   ├── detection/             # BaseOilSpillDetector, ClassicalBaselineDetector, MockDetector, Characterizer, Adapters
│   │   │   ├── environmental/         # EnvironmentalService (Winds, Currents, Waves)
│   │   │   ├── drift/                 # Lagrangian Monte Carlo drift hindcasting engine
│   │   │   ├── ais/                   # CSVAISProvider, MockAISProvider
│   │   │   ├── attribution/           # Explainable 4-factor scoring & evidence engine
│   │   │   └── reporting/             # Forensic investigation report generator
│   │   ├── api/v1/                    # REST API routes (scenes, detection, slicks, drift, ais, attribution, reports, demo)
│   │   └── utils/                     # Geospatial math (haversine, ellipsoidal area, convex hull) & image processing
│   ├── tests/                         # 16 unit & e2e integration tests (100% passing)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                          # Geospatial dashboard (React 18, Vite, TypeScript, Leaflet, TailwindCSS)
├── data/
│   ├── samples/                       # Complete standardized sample datasets with documented contracts
│   └── README.md
├── ml/
│   ├── features/                      # Tabular feature extraction for look-alike discrimination
│   ├── evaluation/                    # IoU, Dice, Precision, Recall benchmarks
│   └── notebooks/                     # Exploratory SAR baseline notebooks
├── scripts/
│   ├── seed_demo_data.py              # Populates database with Arabian Sea scenario
│   └── run_pipeline_cli.py            # CLI tool to run end-to-end pipeline in terminal
├── docs/                              # System architecture, SIH problem analysis, attribution methodology
├── docker-compose.yml                 # Multi-container setup (PostGIS + Backend + Frontend)
├── .env.example                       # Environment variables template
├── Makefile                           # Developer shortcut commands
└── README.md
```

---

## 4. Quickstart Guide

### Prerequisites
- Python 3.12+ (tested on Python 3.13)
- Node.js 18+ & npm
- Docker & Docker Compose (optional for local SQLite mode)

### Option A: Local Run (Zero-Setup SQLite Mode)

1. **Install Backend Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Run the Test Suite**:
   ```bash
   python -m pytest backend/tests -v
   ```

3. **Seed Demo Scenario & Verify CLI Pipeline**:
   ```bash
   python scripts/seed_demo_data.py
   python scripts/run_pipeline_cli.py
   ```

4. **Start Backend Server**:
   ```bash
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
   API Docs available at: `http://localhost:8000/docs`

5. **Start Frontend Dashboard**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

### Option B: Docker Compose (PostGIS + Backend + Frontend)

Start the entire stack with one command:
```bash
docker compose up --build -d
```
- Frontend UI: `http://localhost:3000`
- Backend API & OpenAPI Docs: `http://localhost:8000/docs`
- PostGIS Database: `localhost:5432`

---

## 5. API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | System health check and version metadata |
| `GET` | `/api/v1/scenes` | List ingested satellite scenes |
| `POST`| `/api/v1/scenes/upload` | Ingest or upload a new satellite scene |
| `POST`| `/api/v1/detection/run/{scene_id}` | Execute oil spill segmentation and characterization |
| `GET` | `/api/v1/slicks` | List detected oil slicks with bounding boxes |
| `GET` | `/api/v1/slicks/{id}/geojson` | Export slick as RFC 7946 GeoJSON Feature |
| `GET` | `/api/v1/environment/{slick_id}` | Retrieve wind and ocean current snapshot |
| `POST`| `/api/v1/drift/{slick_id}/simulate` | Run Lagrangian drift simulation / backward hindcast |
| `POST`| `/api/v1/ais/query` | Query vessels in spatial bbox and time window |
| `GET` | `/api/v1/ais/trajectories/{vessel_id}`| Retrieve vessel breadcrumb track |
| `POST`| `/api/v1/attribution/{slick_id}/run` | Execute explainable 4-factor vessel attribution |
| `GET` | `/api/v1/candidates/{slick_id}` | Retrieve ranked candidate polluters |
| `POST`| `/api/v1/reports/{slick_id}/generate` | Generate official PSC forensic investigation report |
| `GET` | `/api/v1/reports/{slick_id}/markdown` | Export investigation report as Markdown |
| `POST`| `/api/v1/demo/seed` | One-click demo seeder for Mumbai Offshore scenario |
| `POST`| `/api/v1/demo/run-e2e` | Execute the complete 8-stage pipeline end-to-end |

---

## 6. How Mock and Baseline Services Work

- **Detection**:
  - `ClassicalBaselineDetector`: Real adaptive Otsu thresholding + dark spot segmentation on SAR raster arrays. Clearly labeled as non-production baseline.
  - `MockOilSpillDetector`: Deterministic geo-referenced test polygon in the Arabian Sea (Mumbai Offshore shipping corridor).
  - `Adapters`: Future U-Net / SegFormer model slots.
- **Drift Simulation**:
  - `MockDriftService`: Real Lagrangian particle advection ($v_{\text{drift}} = v_{\text{current}} + 0.032 \cdot v_{\text{wind}}$) with stochastic turbulent diffusion ($D = 10 \text{ m}^2/\text{s}$). Computes genuine convex hull polygons for origin uncertainty.
- **AIS Provider**:
  - `CSVAISProvider`: Standardized CSV parser reading historical maritime position reports with real Haversine distance, bounding box, and temporal filtering.
  - `MockAISProvider`: Realistic synthetic corridor tracks for testing.
- **Attribution Engine**:
  - `VesselAttributionEngine`: 100% explainable weighted scoring:
    - **Proximity (35%)**: Closest Point of Approach (CPA) inverse distance.
    - **Temporal (25%)**: Consistency with inferred release window ($\sigma = 75$ min).
    - **Trajectory (25%)**: Geometric intersection with 95% uncertainty origin polygon.
    - **Behavior (15%)**: Vessel category prior risk (Tanker vs Tug) + speed anomaly detection.

---

## 7. Future ML Roadmap

1. **Phase 1 (Complete)**: Classical image processing baseline + explainable 4-factor scoring engine.
2. **Phase 2**: Deep learning semantic segmentation with **U-Net** (ResNet-50 backbone) trained on Sentinel-1 SAR imagery.
3. **Phase 3**: Look-alike classification (Random Forest / LightGBM) on texture and meteorological indicators (low-wind suppression, biogenic surfactants).
4. **Phase 4**: Operational integration with **OpenDrift / OpenOil** for full 3D weathering and wave Stokes drift.
5. **Phase 5**: Real-time AIS streaming integration via **AISHub** and **Coast Guard VTS**.
6. **Phase 6**: Learned graph-neural vessel attribution model calibrated against historical Maritime Coast Guard incident records.
7. **Phase 7**: Statistical uncertainty calibration (Conformal Prediction).
8. **Phase 8**: Multi-satellite fusion (SAR + Optical Sentinel-2 + Thermal Landsat-9).

---

## 8. License & Attribution
Developed for Smart India Hackathon 2026 under Problem Statement SIH26143.
Licensed under the MIT License.
