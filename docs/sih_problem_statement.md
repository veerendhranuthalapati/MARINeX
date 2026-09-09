# SIH26143: Problem Statement Analysis

## Problem Title
**SIH26143 — Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill.**

---

## 1. Background & Operational Challenge

Oil pollution at sea presents catastrophic environmental and economic threats to coastal ecosystems, marine fisheries, and maritime security. While major maritime tanker disasters receive high media visibility, over **60% of marine oil contamination results from deliberate operational discharges**:
- Illegal bilge water pumping
- Tank washing residues discharged during darkness or remote transits
- Bunkering leaks in offshore anchorages

Maritime enforcement agencies (such as the **Indian Coast Guard**, **DG Shipping**, and international **Port State Control (PSC)** authorities) face several operational bottlenecks:
1. **Enormous Search Corridors**: The Indian Exclusive Economic Zone (EEZ) spans over 2.3 million square kilometers with thousands of transiting vessels daily.
2. **Weather & Cloud Cover Limitations**: Optical satellites (Sentinel-2, Landsat) are obstructed by clouds and night conditions.
3. **Dynamic Ocean Currents**: Oil drifts and weathers rapidly. By the time a satellite observes a slick, the discharging vessel may be tens or hundreds of kilometers away.
4. **Attribution Burden of Proof**: Under MARPOL 73/78 (Annex I), authorities cannot impound or penalize a ship without rigorous, explainable correlation linking the vessel's trajectory to the spill's physical release coordinates and time.

---

## 2. Solution Strategy: The Multi-Stage Verification Pipeline

MARINeX solves these challenges through a coupled multi-sensor, multi-physics framework:

1. **Synthetic Aperture Radar (SAR) Ingestion**:
   - Sentinel-1 C-SAR emits microwave radiation that penetrates clouds and functions day and night.
   - Oil slicks dampen capillary ocean waves, creating sharp dark patches of radar backscatter suppression.

2. **Morphometric Slick Characterization**:
   - Computes area, perimeter, orientation, and elongation to differentiate linear operational discharges from circular platform seepages.

3. **Backward Lagrangian Particle Hindcasting**:
   - Using 10-meter wind fields (ERA5/GFS) and surface ocean currents (CMEMS), the system reverse-propagates the slick back in time to estimate the exact coordinate and timestamp when the oil touched the water.
   - Monte Carlo particle diffusion estimates an origin uncertainty ellipse/polygon.

4. **Corridor AIS Trajectory Correlation**:
   - Evaluates all candidate vessels within the temporal-spatial envelope.
   - Calculates Closest Point of Approach (CPA) and trajectory-to-origin intersection.

5. **Explainable Forensic Scoring & Dossier**:
   - Compiles an actionable investigation dossier with verifiable evidence bullets, enabling immediate Port State Control boardings at the vessel's destination port.
