# MARINeX Evidence-Driven Investigation Workflow (SIH26143)

MARINeX treats an oil spill as an **incident**, not an isolated slick: every stage
of the pipeline produces a labeled fact (a status label + provenance), and the
system only ever claims what the data actually supports. This document describes
the scientific hierarchy, the status-label vocabulary, the confidence/quality
gates, the conclusion tiers, and how the system refuses to over-claim.

## 1. Scientific Hierarchy

The investigation builds conclusions from foundational observations upward. A
downstream stage may only run if its inputs exist and pass their gates:

```
Satellite
  -> ML (segmentation + calibrated confidence)
    -> Slick (characterization: area, perimeter, compactness)
      -> Environment (wind / current snapshot, quality-checked)
        -> Drift (Lagrangian hindcast/forecast)
          -> Origin (95% uncertainty region + release time)
            -> AIS (vessel tracks in the corridor window)
              -> Candidates (vessels found in spatio-temporal window)
                -> Explainable ranking (4-factor scoring)
                  -> Evidence (ledger records + provenance)
                    -> Report (consolidated conclusion + data quality)
```

Each arrow may be blocked by a gate (SSection 4). Nothing auto-inferred from a
stage that did not run or that failed its quality check.

## 2. Status Labels

Every pipeline output carries exactly one `StatusLabel`
(`backend/app/core/status.py`):

| Label | Meaning |
|---|---|
| `OBSERVED` | Sensor-observed fact (satellite scene, AIS position report). |
| `ML_SEGMENTED` | Slick produced by the production ML segmentation model. |
| `INFERRED` | Derived from a model (e.g. hindcast origin region). |
| `SIMULATED` | Output of a physics simulation (drift). |
| `PREDICTED` | Model prediction output. |
| `TRACKED` | AIS vessel position report. |
| `CANDIDATE` | Ranked investigation candidate (priority, never guilt). |
| `DEMO_DATA` | Synthetic/demo input (never claimed as real). |
| `NOT_AVAILABLE`, `MOCK`, `EXPERIMENTAL`, `UNVALIDATED` | Supplementary markers for unavailable/mock/experimental/unvalidated outputs. |

Detail: these labels ride on every incident, scene, slick, detection run, and
evidence record so the UI and reports never overstate what the data proves.

## 3. Confidence Tiers and Conclusion Tiers

Per-candidate confidence (`ConfidenceTier`): `HIGH`, `MEDIUM`, `LOW`, `EXCLUDED`
(thresholds in `backend/app/services/attribution/engine.py`, see `ATTRIBUTION.md`).

A run-level **conclusion** lands on exactly one of three values:

| Conclusion | Fires when |
|---|---|
| `CANDIDATE_IDENTIFIED` | At least one scanned vessel reaches HIGH evidence consistency. |
| `INSUFFICIENT_EVIDENCE` | Candidates exist but the strongest only reaches LOW/MEDIUM; a cautious review is recommended before any port-state action. |
| `NO_RELIABLE_CANDIDATE` | All scanned vessels are spatially/temporally inconsistent (EXCLUDED), or zero AIS trajectories were found in the window. |

The conclusion is derived from the actual scored candidates, not hard-coded.

## 4. Confidence / Quality Gating

Two explicit gates keep the pipeline honest:

1. **Low-confidence detection blocks auto-attribution (Phase 40).**
   `DetectionService` (`backend/app/services/detection/service.py`) reports
   status `LOW_CONFIDENCE` when detection runs but produces no polygons with
   confidence below the operational minimum. The run is persisted, the incident
   status is set to `LOW_CONFIDENCE` (`backend/app/api/v1/incidents.py`), slick
   creation is skipped, and the system deliberately does **not**
   auto-continue to drift/attribution. The output is flagged for analyst review.

2. **Environment quality FAIL blocks drift.**
   `POST /api/v1/drift/{slick_id}/simulate` runs an `EnvironmentQualityChecker`
   over the requested window (coordinate bounds, timestamp ordering, temporal
   coverage vs provider availability, physical unit ranges). An overall `FAIL`
   returns `422 "Environmental quality check FAILED; drift simulation blocked."`
   with the full check report (`backend/app/api/v1/drift.py`).

`DataQualityService` additionally grades each report by contributing source
(satellite / model / environmental / drift / AIS) and takes the strict
worst-case grade as the overall quality (`backend/app/services/data_quality/service.py`).

## 5. Refusing to Over-Claim

- **No candidate path**: if no AIS vessel trajectories fall in the search window,
  the engine returns `NO_RELIABLE_CANDIDATE` and explicitly states no correlation
  could be performed (no fabrication of a "most likely" vessel).
- **Insufficient evidence path**: if the strongest candidate is only LOW/MEDIUM,
  the conclusion is `INSUFFICIENT_EVIDENCE` with a recommendation for additional
  optical/tracking verification before any port-state action.
- **Candidate status is not guilt**: every ranked vessel is labeled `CANDIDATE`
  (priority), and composite scores are documented as investigation priority, not
  legal proof of liability.
- **DEMO data never masquerades as real**: synthetic inputs are stamped
  `status_label=DEMO_DATA`; reported numbers come from the real production
  algorithms, never hard-coded outcomes (`backend/app/api/v1/demo.py`).

## 6. Incidents API and the Evidence Ledger

The investigation is orchestrated through the incident-centric API
(`backend/app/api/v1/incidents.py`):

- `POST/GET/PATCH /api/v1/incidents[/{id}]` - create/inspect incidents
- `POST /api/v1/incidents/{id}/scenes` - attach a satellite scene
- `POST /api/v1/incidents/{id}/detect` - run detection (sets `NO_SLICKS` /
  `LOW_CONFIDENCE` / `UNDER_INVESTIGATION`)
- `GET|POST /api/v1/incidents/{id}/evidence` - read / append evidence records
- `GET /api/v1/incidents/{id}/drift-reports` - hindcast/forecast simulations
- `GET /api/v1/incidents/{id}/attribution` - ranked candidates with factor scores
- `GET /api/v1/incidents/{id}/origin` - latest hindcast origin (status `INFERRED`)
- `GET /api/v1/incidents/{id}/report` - consolidated report

Every stage appends to the append-only **evidence ledger**
(`backend/app/services/evidence.py`): `DETECTION`, `SLICK`, `ENVIRONMENT`,
`DRIFT`, `AIS`, `CANDIDATE` records, each with a `StatusLabel` and a stampd
provenance object. See `EVIDENCE.md`.

## References

- `backend/app/core/status.py` - status labels, confidence tiers, provenance schema
- `backend/app/services/attribution/engine.py` - scoring and conclusion logic
- `backend/app/services/detection/service.py` - low-confidence gating
- `backend/app/api/v1/drift.py` - environment quality gate
- `backend/app/services/data_quality/service.py` - per-source quality grades
- `backend/app/api/v1/incidents.py` - incident-centric API
- `backend/app/services/evidence.py` - evidence ledger