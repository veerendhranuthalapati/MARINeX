# MARINeX Current State

## Build Status
| Component | Status |
|-----------|--------|
| Backend Python (FastAPI) | ✅ 16/16 tests passing |
| Frontend TypeScript (React/Vite) | ✅ Builds cleanly (0 TS errors) |
| ML Training Pipeline | ✅ 7 model checkpoints present |
| Dataset (120 patches) | ✅ Group-aware split, zero leakage |

## Architecture
- **Backend**: FastAPI + SQLAlchemy + SQLite (local) / PostgreSQL+PostGIS (Docker)
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + Leaflet + MapLibre
- **ML**: PyTorch (U-Net, U-Net++, SegFormer) + scikit-learn (classical baselines)
- **Deployment**: Docker Compose (PostGIS 16 + backend + frontend)

## API Endpoints (12 routers registered)
`/api/v1/scenes`, `/api/v1/detection`, `/api/v1/slicks`, `/api/v1/drift`, `/api/v1/environment`, `/api/v1/attribution`, `/api/v1/reports`, `/api/v1/ais`, `/api/v1/investigations`, `/api/v1/candidates`, `/api/v1/health`, `/api/v1/demo`

## Frontend Pages (9 routes)
Dashboard, Scenes, Detection, Drift, Investigation, Candidates, Reports, AIS Analysis, 404

## Type System
Frontend `types/index.ts` has been aligned with backend Pydantic schemas, with backward-compatible legacy fields for map components that use older naming conventions (e.g., `centroid_lat`/`centroid_lon` alongside `centroid[]`, `area_sqkm` alongside `area_km2`).

## Known Limitations
- SQLite mode (no PostGIS spatial queries) — works for demo
- Map components use legacy field names with fallbacks to backend-aligned fields
- Demo data seeded via `scripts/seed_demo_data.py` for Mumbai Offshore scenario
- Chunk size warning on build (1.9MB JS bundle) — code splitting recommended for production

## Files Modified This Session
- `frontend/src/types/index.ts` — Complete rewrite to match backend schemas
- `frontend/src/components/investigation/CategoryBadge.tsx` — Re-export from ui/
- `frontend/src/components/investigation/RadialScore.tsx` — Re-export from ui/
- `frontend/src/pages/ScenesPage.tsx` — Fixed type imports and property access
- `frontend/src/pages/DetectionPage.tsx` — Fixed property names (source, resolution, slicks_detected)
- `frontend/src/pages/DriftPage.tsx` — Fixed area_km2 and particles references
- `frontend/src/pages/InvestigationPage.tsx` — Fixed centroid, wind, current, wave access
- `frontend/src/pages/ReportsPage.tsx` — Fixed Investigation import source
- `frontend/src/services/api.ts` — Changed to `import type`
- `frontend/src/components/map/MapLibreMap.tsx` — Fixed optional mmsi access
- `frontend/src/components/map/MarineMap.tsx` — Fixed all optional property access
- `frontend/src/components/investigation/EvidenceDrawer.tsx` — Fixed optional chaining
