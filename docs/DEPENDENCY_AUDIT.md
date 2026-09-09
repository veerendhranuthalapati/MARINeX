# MARINeX Dependency Audit

## Frontend (npm)
All dependencies installed and compatible. No security advisories detected.

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.x | UI framework |
| react-dom | 18.x | DOM rendering |
| react-router-dom | 7.x | Client-side routing |
| typescript | 5.x | Type checking |
| vite | 6.x | Build tool |
| @vitejs/plugin-react | 4.x | React SWC transform |
| tailwindcss | 3.x | Utility CSS |
| postcss + autoprefixer | latest | CSS processing |
| motion (framer-motion) | 12.x | Animations |
| leaflet + react-leaflet | latest | Map rendering |
| maplibre-gl | 4.x | Vector tile maps |
| zustand | 5.x | State management |
| recharts | 2.x | Chart library |
| lucide-react | latest | Icon library |
| @tanstack/react-table | 8.x | Data tables |
| clsx + tailwind-merge | latest | Classname utilities |
| vite-plugin-comlink | 6.x | Service worker bundling |

**Note**: `vite-plugin-comlink` is installed but not used in vite.config.ts — candidate for removal.

## Backend (pip)
All dependencies installed. No conflicts detected.

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | latest | HTTP framework |
| uvicorn | latest | ASGI server |
| sqlalchemy | latest | ORM |
| pydantic | latest | Data validation |
| numpy | latest | Numerical computing |
| pandas | latest | Data manipulation |
| scikit-learn | latest | ML utilities |
| scipy | latest | Scientific computing |
| shapely | latest | Geometric operations |
| geopy | latest | Geographic utilities |
| h5py | latest | HDF5 file I/O |
| rasterio | latest | Raster data I/O |
| matplotlib | latest | Plotting |
| pytest | latest | Test framework |
| pytest-asyncio | latest | Async test support |
| httpx | latest | HTTP client |
| pillow | latest | Image processing |

## ML (PyTorch)
| Package | Version | Purpose |
|---------|---------|---------|
| torch | 2.x | Deep learning framework |
| torchvision | 0.x | Vision models/transforms |
| segmentation-models-pytorch | 0.x | Pre-built segmentation architectures |

## Docker
| Image | Version | Purpose |
|-------|---------|---------|
| postgis/postgis | 16-3.4 | PostgreSQL + PostGIS |
| Node (frontend) | 22-alpine | Frontend build |
| Python (backend) | 3.13-slim | Backend runtime |

## Security Notes
- No known CVEs in current dependency versions
- Docker images use official base images
- Backend secrets managed via environment variables
- SQLite used for local dev only — PostgreSQL for staging/production
