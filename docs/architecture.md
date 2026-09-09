# MARINeX System Architecture (SIH26143)

MARINeX is a modular geospatial intelligence platform designed for **Smart India Hackathon 2026 Problem SIH26143**:
*"Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill."*

---

## 1. End-to-End Pipeline Architecture

```mermaid
flowchart TD
    subgraph Satellite Ingestion
        A1[Copernicus Sentinel-1 SAR / Sentinel-2 MSI] --> A2[Scene Metadata Extraction & Geo-referencing]
        A2 --> A3[(Scene Database)]
    end

    subgraph Detection & Characterization
        A3 --> B1[Oil Spill Detection Engine]
        B1 -->|Classical Adaptive Otsu| B2[Candidate Dark Spot Mask]
        B1 -.->|Future U-Net / SegFormer| B2
        B2 --> B3[Slick Characterization Engine]
        B3 -->|Area, Perimeter, Centroid, Bbox, Compactness| B4[(Oil Slick Entities)]
    end

    subgraph Drift Hindcasting
        B4 --> C1[Environmental Data Service]
        C1 -->|Copernicus Marine / ERA5| C2[Wind & Ocean Current Vectors]
        C2 --> C3[Lagrangian Particle Hindcast Service]
        C3 -->|Negative Time Integration| C4[Probable Origin Centroid & 95% Uncertainty Hull]
    end

    subgraph AIS Correlation & Attribution
        C4 --> D1[AIS Provider / Spatial Corridor Filter]
        D1 -->|Historical CSV / Live Stream| D2[Vessel Trajectory Reconstruction]
        D2 --> D3[Explainable Vessel Attribution Engine]
        C4 --> D3
        D3 -->|Proximity, Temporal, Trajectory, Behavior| D4[Ranked Candidate Polluters & Forensic Evidence]
    end

    subgraph Presentation & Reporting
        B4 --> E1[Interactive Geospatial Command Center]
        C4 --> E1
        D4 --> E1
        E1 --> E2[Forensic Investigation Report Generator]
        E2 --> E3[PSC Inspection Dossier / Markdown Export]
    end
```

---

## 2. Core Domain Components

### A. ML Detection Service (`app/services/detection/`)
- **`BaseOilSpillDetector`**: Abstract interface defining `predict()`, `segment()`, `confidence()`, and `metadata()`.
- **`ClassicalBaselineDetector`**: Explainable baseline using adaptive Otsu thresholding on SAR normalized radar cross section ($\sigma^0$), morphological opening/closing to filter ocean speckle noise, and contrast measurement in dB.
- **`MockOilSpillDetector`**: Deterministic synthetic polygon generator for integration tests.
- **`Adapters`**: Plug-and-play adapter classes for PyTorch U-Net, DeepLabV3+, and SegFormer models.

### B. Slick Characterization Engine (`app/services/detection/characterizer.py`)
Calculates physical morphometrics from binary masks and polygons:
- **Geodesic Area ($km^2$)**: Scaled metric integration across WGS-84 ellipsoidal coordinates.
- **Perimeter ($km$)**: Great-circle boundary length.
- **Centroid**: Center of mass in `[longitude, latitude]`.
- **Oriented Minimum Bounding Box**: Calculates length of major axis, width of minor axis, and orientation angle.
- **Compactness**: Isoperimetric circularity quotient $4 \pi \cdot \text{Area} / \text{Perimeter}^2$.

### C. Drift Simulation & Hindcasting (`app/services/drift/`)
- Integrates net surface velocity:
  $$\vec{v}_{\text{net}} = \vec{v}_{\text{current}} + \alpha \cdot \vec{v}_{\text{wind}}$$
  where $\alpha \approx 0.032$ (leeway wind drift factor).
- Backward integration with stochastic Gaussian turbulent diffusion:
  $$\Delta x_{\text{diff}} = R_x \sqrt{2 D \Delta t}, \quad \Delta y_{\text{diff}} = R_y \sqrt{2 D \Delta t}$$
- Computes convex hull around dispersed particle cloud at $t_{\text{origin}}$ to represent the **95% Probable Origin Region**.

### D. AIS Provider & Spatio-Temporal Filter (`app/services/ais/`)
- Standardized `AISProvider` interface.
- `CSVAISProvider`: Efficient spatial bounding box and temporal window filtering with trajectory interpolation.
- `MockAISProvider`: Realistic synthetic maritime corridor traffic generator.

### E. Vessel Attribution Engine (`app/services/attribution/`)
Computes four independent, explainable factor scores:
1. **Proximity Score ($S_{\text{prox}}$)**: Exponential decay from origin centroid at Closest Point of Approach (CPA).
2. **Temporal Score ($S_{\text{temp}}$)**: Gaussian consistency with hindcast origin release time ($\sigma = 75$ min).
3. **Trajectory Score ($S_{\text{traj}}$)**: Direct geometric intersection with origin uncertainty polygon.
4. **Behavior Score ($S_{\text{behav}}$)**: Cargo risk classification (Crude Tanker vs Tug) and transit speed anomalies.

Composite Candidate Score:
$$S_{\text{overall}} = w_{\text{prox}} S_{\text{prox}} + w_{\text{temp}} S_{\text{temp}} + w_{\text{traj}} S_{\text{traj}} + w_{\text{behav}} S_{\text{behav}}$$
All scores are accompanied by audit-trail natural language forensic evidence points.
