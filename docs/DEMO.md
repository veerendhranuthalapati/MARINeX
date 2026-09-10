# MARINeX Demo Cases (SIH26143)

`POST /api/v1/demo/cases/{id}` executes five scripted demonstration scenarios
(cases A-D plus a complete incident). Every case runs the **real backend
algorithms** (drift, attribution, data quality, conclusion tiers, state
transitions) on clearly-labeled synthetic scenario inputs. The synthetic inputs
themselves are generated in-code and stamped `status_label=DEMO_DATA`.

## 1. Honest Labeling

- All demo scenario inputs (extra AIS tracks, low-signal rasters, constructed
  slicks) carry `status_label=DEMO_DATA` in their provenance and vessel metadata.
- Reported numbers (conclusions, scores, data-quality grades, origin geometry)
  are **computed by the production engine at runtime - never hard-coded**.
- The demo module carries the explicit rule: *"Outcomes are never faked."*
  (see the case runner in `backend/app/api/v1/demo.py`).

## 2. Anti-Fabrication Rule

The demo exists to demonstrate the pipeline's behavior, including its refusal
paths. It must therefore be possible for a case to conclude
`NO_RELIABLE_CANDIDATE` or `INSUFFICIENT_EVIDENCE`, and only the stage outputs
that actually exist are reported. A case cannot invent evidence that its inputs
did not produce; when evidence is weak or absent the honest conclusion is
returned.

## 3. Cases

| Case | Scenario | Expected behavior / conclusion |
|---|---|---|
| `case_a_high_confidence` | Slick + 3.5 h drift hindcast + a DEMO AIS *crude-oil tanker* crossing the origin polygon at release time (plus a cargo vessel passing nearby). | Real drift + real scoring -> a HIGH-confidence candidate; conclusion `CANDIDATE_IDENTIFIED`. |
| `case_b_low_confidence` | Real demo SAR raster physically degraded +3 dB (radiometric shift) run through the frozen production UNet. | Detection drops below threshold -> `LOW_CONFIDENCE` gate: flagged for analyst review, `automatic_attribution_run: false`, no auto-continue to drift/attribution (Phase 40). |
| `case_c_multi_candidate` | Standard demo corridor with the historical AIS traffic (5 vessels) scanned by the pipeline. | Ranked multi-vessel matrix with per-factor scores and an honest conclusion + `data_quality` block. |
| `case_d_no_candidate` | Slick constructed ~150 km from the demo corridor where no AIS traffic exists. | Zero trajectories scanned -> conclusion `NO_RELIABLE_CANDIDATE`; no port-state escalation recommended. |
| `incident_complete` | Full evidence chain on the seeded Mumbai Offshore incident: scene, detection, characterization, environment, drift, origin, AIS, attribution, report, evidence ledger, provenance. | Returns the 13-artifact summary, conclusion, `data_quality`, evidence types, and the report Markdown. |

## 4. Sample Data Files Used

The demo reads from the committed sample bundle (`data/samples/`):

- `sample_scene_sentinel1_sar.json` + `imagery/sentinel1_20260301_sar_sample.png` - scene + raster
- `sample_environmental.json` - wind/current/wave snapshot
- `sample_ais_trajectories.csv` - historical AIS traffic (corridor)
- `sample_drift_hindcast.geojson`, `sample_oil_slick.geojson`, `sample_candidates.json` - documented sample outputs

Scenario-specific inputs (case A tanker/cargo tracks, case B degraded raster,
case D remote slick) are produced in-code and labeled `DEMO_DATA`.

## References

- `backend/app/api/v1/demo.py` - case runner and case builders
- `backend/tests/test_demo_cases_and_ml.py` - automated coverage of all five cases
- `data/samples/README.md` - sample data contracts