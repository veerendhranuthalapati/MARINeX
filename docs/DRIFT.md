# MARINeX Drift Simulation & Hindcasting (SIH26143)

The drift service reconstructs where an oil slick came from (hindcast) or where
it is going (forecast) using a deterministic Lagrangian Monte Carlo particle
model. All drift output is labeled `SIMULATED` on the evidence ledger.

## 1. Service

`MockDriftService` (`backend/app/services/drift/service.py`) provides:

- **Backward-in-time integration (HINDCAST)** from the slick centroid to infer
  the probable spill release location and time.
- **Forward integration (FORECAST)** from the slick centroid.
- **Net advection velocity** combining ocean current and wind leeway:

  ```
  v_net = v_current + alpha * v_wind
  ```

  with default leeway factor `alpha = 0.032` (3.2% of the 10 m wind vector).
- **Stochastic horizontal turbulent diffusion** with coefficient
  `D = 10 m^2/s`; each step perturbs particles by `sqrt(2 * D * dt)`.
- Model identifier: `LAGRANGIAN_MONTE_CARLO_DRIFT_v1`.

Inputs (wind u/v, current u/v) come from `EnvironmentalService`
(`backend/app/services/environmental/service.py`), which reads the sample
environmental snapshot or a calibrated default baseline.

## 2. Outputs

| Output | Description |
|---|---|
| `probable_origin_centroid` | Mean particle position at origin time. |
| `probable_origin_time` | `start_time - duration_hours` for HINDCAST. |
| `origin_geometry` | Convex hull around the dispersed particle cloud (95% Probable Origin Region). |
| `trajectory_geometry` | Mean centerline back-track (LineString). |
| `uncertainty` | `diffusion_radius_km = 1.96 * std(x)` (95%), `total_drift_distance_km`, `drift_speed_knots`. |
| `particles` | Sub-sample (max 80) of particle positions for rendering. |

## 3. Determinism

The simulation seeds its RNG with `numpy.random.default_rng(42)` internally, so
**identical inputs always produce identical outputs**:

- `reports/drift_sanity_results.json` -> `determinism`: two identical runs
  produced the same origin centroid (`71.25087, 19.27465`) and the identical
  uncertainty object; `same_centroid == same_uncertainty == true`, `passed == true`.

This makes every drift report reproducible and auditable, at the cost of not
sampling forcing uncertainty (see Limitations).

## 4. Physics Sanity Tests

`scripts/drift_sanity_tests.py` runs three constant-forcing checks (no wind,
24 h hindcast, 200 particles):

| Check | Inputs | Expected | Result |
|---|---|---|---|
| `eastward_current` | 0.5 m/s east | origin west of centroid (43.12 km drift) | PASS |
| `northward_current` | 0.5 m/s north | origin south of centroid (43.10 km drift) | PASS |
| `zero_forcing` | 0.0 m/s | origin near centroid (0.13 km drift) | PASS |

All entries in `reports/drift_sanity_results.json` report `passed: true`
(aggregate `ALL PASSED`).

## 5. Sensitivity Analysis

The same script sweeps 15 scenarios and writes `reports/drift_sensitivity.csv`:

- `duration_sweep` (3): 12 / 24 / 36 h -> drift 13.76 / 27.45 / 41.30 km.
- `wind_uncertainty` (4): 0.5x-1.5x wind vector modifiers.
- `current_uncertainty` (4): 0.5x-1.5x current vector modifiers.
- `position_sensitivity` (4): +-0.01 deg centroid offsets.

Expected qualitative behavior is observed (longer duration and stronger currents
increase drift distance; the diffusion radius grows with duration: 1.66 / 2.45 /
3.10 km) and confirms output stability under small perturbations.

## 6. Quality Gating Before Simulation

`POST /api/v1/drift/{slick_id}/simulate` first runs an `EnvironmentQualityChecker`
(`backend/app/services/environmental/quality.py`) on the requested
spatio-temporal window:

- coordinate-system / WGS84 bounds sanity
- timestamp ordering / timezone consistency
- temporal coverage vs provider availability (6 h margin)
- physical unit ranges (wind, current, wave height)

If the overall grade is `FAIL`, the endpoint returns HTTP 422 and does **not**
run the simulation:
`"Environmental quality check FAILED; drift simulation blocked."` A `WARN`
grade is carried into provenance rather than hard-blocked.

## 7. Limitations (honest)

- **Deterministic baseline**: forcing is a single snapshot from the sample
  environment file; the RNG is fixed, so forcing uncertainty is not propagated
  into the uncertainty envelope.
- **Not reanalysis-fed**: the ERA5/CMEMS adapter (`era5_provider.py`) is stubbed;
  no live reanalysis download is wired in.
- **Physics scope**: no 3D hydrodynamic Stokes drift, evaporation weathering, or
  wave-induced mixing (planned OpenDrift/OpenOil adapter).

## References

- `backend/app/services/drift/service.py` - MockDriftService
- `backend/app/services/environmental/service.py` - EnvironmentalService
- `backend/app/services/environmental/quality.py` - EnvironmentQualityChecker
- `backend/app/api/v1/drift.py` - API + quality gate
- `scripts/drift_sanity_tests.py` - sanity / determinism / sensitivity runner
- `reports/drift_sanity_results.json`, `reports/drift_sensitivity.csv`