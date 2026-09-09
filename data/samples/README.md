# MARINeX Data Contracts & Sample Schemas

This directory contains standardized data contracts, JSON schemas, and sample datasets for the SIH26143 oil spill detection and AIS vessel attribution pipeline.

---

## 1. Satellite Scene Metadata (`sample_scene_sentinel1_sar.json`)

Describes the raw satellite observation footprint and acquisition parameters.

| Field | Type | Description |
|---|---|---|
| `id` | String | Unique scene identifier (e.g. `scene_s1a_20260301_arabian_sea_001`). |
| `source` | String | Satellite platform name (e.g. `Copernicus Sentinel-1A`). |
| `sensor` | String | Sensor type (e.g. `C-SAR (Synthetic Aperture Radar)`). |
| `mode` | String | Acquisition mode (e.g. `IW (Interferometric Wide Swath)`). |
| `polarization` | String | Radar polarization channels (e.g. `VV+VH`). |
| `acquisition_time` | ISO 8601 UTC | Timestamp when sensor scanned the region. |
| `latitude`, `longitude`| Float | Scene center coordinates in WGS-84 decimal degrees. |
| `bounding_box` | Array [4] | `[min_lon, min_lat, max_lon, max_lat]`. |
| `resolution_meters` | Float | Ground sample distance / spatial resolution in meters. |
| `file_path` | String | Local path or Cloud Object Store (GCS/S3) URI for scene raster. |
| `status` | String | Ingestion status (`INGESTED`, `PROCESSING`, `ERROR`). |

---

## 2. Oil Slick Detection (`sample_oil_slick.geojson`)

Standard RFC 7946 GeoJSON `FeatureCollection` representing detected oil spill contours and physical attributes.

| Property | Type | Description |
|---|---|---|
| `slick_id` | String | Unique identifier of the detected slick. |
| `scene_id` | String | Foreign key to parent satellite scene. |
| `detection_method` | String | Detector algorithm (`CLASSICAL_BASELINE_ADAPTIVE_THRESHOLD`, `UNET_RESNET50`, `MOCK_DETECTOR`). |
| `detected_at` | ISO 8601 UTC | Detection timestamp. |
| `confidence` | Float (0-1) | Statistical or model confidence score. |
| `area_km2` | Float | Surface slick footprint in square kilometers. |
| `perimeter_km` | Float | Contour perimeter in kilometers. |
| `centroid` | Array [2] | Center of mass `[longitude, latitude]`. |
| `length_km`, `width_km`| Float | Principal axes of minimum oriented bounding box. |
| `orientation_deg` | Float | Orientation angle in degrees clockwise from North. |
| `compactness` | Float (0-1) | Circularity ratio: $4 \pi \cdot \text{Area} / \text{Perimeter}^2$. |
| `backscatter_contrast_db` | Float | SAR radar backscatter suppression relative to sea clutter. |
| `look_alike_risk` | Enum | Risk that slick is a natural look-alike (`LOW`, `MEDIUM`, `HIGH`). |

---

## 3. Environmental Snapshot (`sample_environmental.json`)

Wind and ocean current observations driving the drift hindcast simulation.

| Field | Type | Description |
|---|---|---|
| `timestamp` | ISO 8601 UTC | Observation or forecast epoch. |
| `source` | String | Data provider (e.g. `Copernicus Marine Service`, `NOAA GFS`, `ERA5`). |
| `wind.speed_mps` | Float | 10-meter surface wind speed in m/s. |
| `wind.direction_deg` | Float | Direction wind is blowing **from** (meteorological degrees). |
| `wind.u_component_mps`, `v_component_mps` | Float | Zonal (eastward) and meridional (northward) wind components. |
| `ocean_current.speed_mps` | Float | Surface current speed in m/s. |
| `ocean_current.u_component_mps`, `v_component_mps` | Float | Zonal and meridional surface water velocity components. |
| `wave.significant_wave_height_m` | Float | Significant wave height in meters ($H_s$). |

---

## 4. Drift Simulation Hindcast (`sample_drift_hindcast.geojson`)

Results of backward Lagrangian particle trajectory simulation.

| Property | Type | Description |
|---|---|---|
| `simulation_id` | String | Simulation execution ID. |
| `simulation_mode` | Enum | `HINDCAST` (reverse time to origin) or `FORECAST` (forward time). |
| `model_name` | String | Drift model algorithm identifier. |
| `probable_origin_time` | ISO 8601 UTC | Inferred timestamp when oil was released into the water. |
| `probable_origin_centroid`| Array [2] | Coordinates of highest probability release point. |
| Features | GeoJSON Features | Contains `PROBABLE_ORIGIN_POLYGON` (95% uncertainty envelope) and `DRIFT_TRAJECTORY` (centerline). |

---

## 5. AIS Trajectories (`sample_ais_trajectories.csv`)

Vessel position reports (breadcrumbs) along shipping lanes.

| Column | Type | Example | Description |
|---|---|---|---|
| `mmsi` | Integer | 636019842 | Maritime Mobile Service Identity (unique 9-digit vessel ID). |
| `imo` | Integer | 9456789 | International Maritime Organization number. |
| `vessel_name` | String | PACIFIC CROWN | Ship name. |
| `vessel_type` | String | Crude Oil Tanker | Ship classification (Tanker, Cargo, Tug, Fishing, etc.). |
| `flag` | String | Liberia | Vessel registry flag state. |
| `timestamp` | ISO 8601 UTC | 2026-03-01T03:25:00Z | AIS report timestamp. |
| `latitude` | Float | 19.310 | Latitude in decimal degrees. |
| `longitude` | Float | 71.376 | Longitude in decimal degrees. |
| `speed_knots` | Float | 11.8 | Speed over ground (SOG) in knots. |
| `course_deg` | Float | 60.0 | Course over ground (COG) in degrees. |
| `heading_deg` | Integer | 60 | True heading in degrees. |
| `nav_status` | String | Under way using engine | Navigation status code / text. |

---

## 6. Vessel Attribution & Evidence (`sample_candidates.json`)

Explainable multi-factor scoring and ranking for candidate polluters.

| Field | Type | Description |
|---|---|---|
| `rank` | Integer | Investigation priority ranking (1 = highest priority). |
| `overall_score` | Float (0-100) | Weighted composite evidence score. |
| `factors.proximity_score` | Float (0-100) | Score based on inverse distance to origin at Closest Point of Approach (CPA). |
| `factors.temporal_score` | Float (0-100) | Score based on time difference between vessel transit and inferred spill time. |
| `factors.trajectory_score`| Float (0-100) | Score reflecting geometric intersection with uncertainty polygon. |
| `factors.behavior_score` | Float (0-100) | Vessel risk profile (tanker vs tug, speed anomaly, loitering). |
| `evidence` | Array of Strings | Human-readable forensic findings explaining the score. |
| `investigation_recommendation` | String | Actionable next steps for maritime authorities / coast guard. |
