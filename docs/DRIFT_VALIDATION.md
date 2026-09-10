# MARINeX Drift Validation (SIH26143)

Final-phase drift module validation. Complements `docs/DRIFT.md` (module
reference) with the closing evidence set and the extended physics checks that
close the earlier east/north-only gap.

## 1. Physics sanity — all four cardinal currents + zero (PASS)

`scripts/drift_sanity_tests.py` (24 h hindcast, 200 particles, no wind) now
checks every required constant forcing — east, **west**, north, **south** and
zero:

| Check | Forcing | Expected | Observed | Result |
|---|---|---|---|---|
| `eastward_current` | 0.5 m/s east | origin west of centroid | lon 71.08898 < 71.5 (43.12 km) | PASS |
| `westward_current` | 0.5 m/s west | origin east of centroid | lon 71.91158 > 71.5 (43.18 km) | PASS |
| `northward_current` | 0.5 m/s north | origin south of centroid | lat 18.96242 < 19.35 (43.10 km) | PASS |
| `southward_current` | 0.5 m/s south | origin north of centroid | lat 19.73987 > 19.35 (43.35 km) | PASS |
| `zero_forcing` | 0 m/s | origin ≈ centroid | 0.131 km < 5 km | PASS |

Aggregate: **ALL PASSED**. Artifact `reports/drift_sanity_results.json`.

## 2. Determinism (PASS)

Identical inputs → identical origin centroid and identical uncertainty object
(`reports/drift_sanity_results.json` → `determinism.passed: true`). Every drift
report is byte-reproducible and auditable.

## 3. Sensitivity (15 scenarios)

`reports/drift_sensitivity.csv`: duration sweep (12/24/36 h → 13.76/27.45/41.30
km), wind ±50%, current ±50%, position ±0.01° — qualitative behavior confirmed
(drift grows with duration/forcing; diffusion radius 1.66/2.45/3.10 km),
outputs stable under small perturbations.

## 4. Forward forecast (Phase 24-25 requirement, already in API)

`MockDriftService` supports both directions: `HINDCAST` (backward integration →
probable origin centroid + 95% uncertainty hull + probable origin time) and
`FORECAST` (forward integration for future slick position). Direction is a
top-level field of the drift request and is covered by backend tests
(`backend/tests`, 35/35). Real +6/+12/+24/+48 h forecast horizons are
achievable through the same service; forcing remains the sample snapshot.

## 5. Quality gating before simulation

`POST /api/v1/drift/{slick_id}/simulate` runs `EnvironmentQualityChecker`
(WGS84 bounds, timestamp ordering/timezone, 6 h temporal-coverage margin,
physical unit ranges). Grade FAIL → HTTP 422, simulation not run; WARN is
carried into provenance (tested in backend suite).

## 6. Evidence labeling

All drift outputs (origin centroid, origin geometry, trajectory, uncertainty)
are persisted to the evidence ledger as `SIMULATED`/`INFERRED` records with
provenance — consistent with the "no unlabeled claim" rule.

## 7. Honest limitations

- Deterministic baseline: single forcing snapshot, fixed RNG — forcing
  uncertainty is NOT propagated into the uncertainty envelope.
- Not reanalysis-fed: ERA5/CMEMS adapter stubbed; no live download.
- No 3-D hydrodynamics/weathering/wave-mixing (planned OpenDrift/OpenOil
  adapter).
- Simulated on synthetic slick geometry; drift verification is on synthetic
  trajectories, not a real spill event.