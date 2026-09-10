# MARINeX Explainable Vessel Attribution (SIH26143)

The attribution engine correlates candidate vessels against the drift-hindcast
origin region and release window, and produces a fully explainable composite
score from four independent factor scores. Every score is auditable via its
factor breakdown and natural-language evidence lines.

## 1. Four-Factor Scoring

Implemented in `backend/app/services/attribution/engine.py`
(`VesselAttributionEngine`). Each factor returns 0-100.

| Factor | Weight | Formula / falloff |
|---|---|---|
| Proximity | 0.35 | Exponential inverse distance from origin at Closest Point of Approach: `100 * exp(-d / 4.8)` (100 at 0 km, ~60 at 2.5 km, ~36 at 5 km, <5 at 15 km). |
| Temporal | 0.25 | Gaussian consistency with the inferred release window: `100 * exp(-(dt / 75 min)^2)` on the CPA-vs-origin-time difference. |
| Trajectory | 0.25 | 92.0 if the vessel track directly intersects the 95% origin uncertainty polygon; otherwise `75 * exp(-dist / 3.5)` distance decay from the polygon (cap 75). |
| Behavior | 0.15 | Vessel-category risk prior: tanker family 75; cargo/container/bulk 40; tug/supply/offshore 25; other 15. A speed anomaly (range > 4.5 kn across >= 3 fixes) adds +15. |

Composite score:

```
overall = 0.35*Proximity + 0.25*Temporal + 0.25*Trajectory + 0.15*Behavior
```

Weights default to `WEIGHT_PROXIMITY/TEMPORAL/TRAJECTORY/BEHAVIOR` in
`backend/app/core/config.py` (0.35 / 0.25 / 0.25 / 0.15) and can be overridden
per-run.

## 2. Confidence Tiers (per candidate)

| Tier | Score | Recommendation |
|---|---|---|
| HIGH | >= 75 | PRIORITY_1: formal maritime query, request Oil Record Book (Part II) + VDR. |
| MEDIUM | 50-75 | PRIORITY_2: monitor secondary AIS tracks, correlate with port inspection records. |
| LOW | 25-50 | PRIORITY_3: low evidence correlation; maintain passive tracking log. |
| EXCLUDED | < 25 | Spatially/temporally inconsistent with inferred origin. |

Candidates are ranked by descending `overall_score`; each carries a
`factors` breakdown, `metrics` (closest distance, time delta, intersection
flag, transit speed, anomaly flag), evidence lines, and an investigation
recommendation.

## 3. Conclusion Tiers (per run)

A run lands on exactly one conclusion, derived from the actual scored
candidates:

| Conclusion | Fires when |
|---|---|
| `CANDIDATE_IDENTIFIED` | Top-ranked candidate reaches HIGH. |
| `INSUFFICIENT_EVIDENCE` | Candidates exist but the top is only LOW/MEDIUM; additional optical/tracking verification recommended before any port-state action. |
| `NO_RELIABLE_CANDIDATE` | All scanned vessels are EXCLUDED, or zero AIS trajectories were found in the search window (correlation cannot be performed). |

The engine never fabricates a "most likely" vessel when the evidence is absent
or weak.

## 4. Explicit Scope Statement

Composite scores represent **relative investigation priority and forensic
consistency only**. They are **not legal proof of liability**; enforcement
actions require the full evidence dossier and further verification. This
statement is embedded in the engine docstring and mirrored in the demo
honesty notes.

## 5. Evidence Trail

For each candidate the engine emits human-readable evidence lines: direct
intersection of the 95% origin polygon, closest-approach distance to centroid,
temporal offset from release window, high-risk cargo classification, and speed
anomaly detection. These land on the incident evidence ledger as `CANDIDATE`
records (`EVIDENCE.md`).

Trajectory geometry validation (the math behind the Trajectory factor) is
documented in `reports/ais_trajectory_validation.json` (east / north+gap /
90-degree-turn all PASS, error ~0.112%).

## References

- `backend/app/services/attribution/engine.py` - scoring, tiers, conclusions
- `backend/app/core/config.py` - default weights
- `backend/app/services/evidence.py` - candidate evidence records
- `reports/ais_trajectory_validation.json` - trajectory geometry validation
- `docs/ATTRIBUTION.md` (this file) - the backend attribution implementation;
  `docs/vessel_attribution_methodology.md` holds the classical methodology write-up