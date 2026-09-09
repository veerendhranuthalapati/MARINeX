# Sentinel-1 SAR Oil Spill Dataset Audit Report

## 1. Inventory & Sensor Telemetry
- **Dataset Root Directory**: `C:\Users\veere\Desktop\MARINeX\data\datasets\sentinel1_primary`
- **Sensor Platform**: Sentinel-1 C-Band SAR (Interferometric Wide Swath Mode - IW)
- **Polarizations**: Dual-Pol `VV` + `VH` + Derived Polarimetric Difference `(VV - VH)`
- **Spatial Resolution**: 10 meters / pixel
- **Total Paired Samples**: 120
- **Corrupted / Unreadable Files**: 0 (0.00%)
- **Duplicate File Groups**: 0
- **Image Dimensions**: 256 × 256 pixels (2.56 km × 2.56 km ground footprint)

## 2. Class Distribution & Imbalance Analysis
- **Total Sample Patches**: 120
- **Patches Containing Mineral Oil Spills**: 60 (50.0%)
- **Patches Containing Look-alikes**: 60 (50.0%)
- **Clean Ocean Clutter Patches**: 24 (20.0%)
- **Zero-Mask Percentage (Negative Class Background)**: 20.0%
- **Mean Oil Foreground Pixel Ratio**: 7.47%
- **Max Oil Foreground Pixel Ratio**: 16.64%

## 3. Leakage Prevention Protocol
- **Partitioning Hierarchy**: Partitioned strictly by **parent Sentinel-1 acquisition scene ID**.
- **Parent Scenes in Training Split**: 8 scenes (80 patches)
- **Parent Scenes in Validation Split**: 2 scenes (20 patches)
- **Parent Scenes in Test Split**: 2 scenes (20 patches)
- **Scene Overlap Across Splits**: **0 scenes (Zero Leakage Verified)**
- **SHA-256 Hash Collision Overlap**: **0 files**
- **Leakage Verification Audit**: `PASSED: Zero leakage between parent scenes and splits`

## 4. Radiometric and Value Range Checks
- **Data Type**: `uint8`
- **Channel 0 (VV)**: Normalized radar cross section, calibrated Bragg sea clutter and Marangoni damping.
- **Channel 1 (VH)**: Cross-polarization channel capturing volume scattering and depolarization.
- **Channel 2 (Pol Diff)**: Polarization ratio anomaly highlighting surface tension reduction.
- **NaN / Inf Occurrences**: 0 detected across all bands.
