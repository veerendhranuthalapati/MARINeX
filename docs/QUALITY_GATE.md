# MARINeX Quality Gate Checklist (SIH26143)

A 31-item release gate for the MARINeX repository before the final commit and
push to `origin`. Every item is verified by running its command or by inspecting
the referenced artifact; nothing is asserted without evidence.

Legend: `[x]` complete, `[ ]` pending.

## Checked Items

- [x] 1. Backend test suite passes: `pytest backend/tests` -> 35 tests passing.
- [x] 2. Frontend TypeScript typecheck passes: `tsc --noEmit` (exit 0).
- [x] 3. Frontend production build succeeds (`npm run build`).
- [x] 4. Production ML model frozen and exported: `models/best_model/marinex_unet_v1.pt`
      (marinex-unet-v1.0.0) with `models/production/metadata.json` generated.
- [x] 5. Frozen test metrics recorded: IoU 0.8857, Dice 0.9394, Precision 0.9080,
      Recall 0.9731, FPR 0.0041, object-F1 0.7901.
- [x] 6. Probability calibration applied: temperature 0.2262; ECE 0.1735 -> 0.0046;
      Brier 0.0330 -> 0.0025 (`models/production/metadata.json`, `reports/calibration.json`).
- [x] 7. Multi-seed stability recorded: seed 42 (IoU 0.9459 / Dice 0.9722),
      seed 123 (0.9358 / 0.9668), seed 999 (0.9265 / 0.9619).
- [x] 8. Dataset split verified: sentinel1-primary, 120 samples, 80/20/20
      train/val/test, group-aware across parent scenes, zero leakage.
- [x] 9. Robustness report present: `reports/robustness/robustness_report.md`
      (7 deterministic perturbation conditions).
- [x] 10. Scene-level generalization report present: `reports/scene_level_report.md`
      (SCENE_02 IoU 0.9034, SCENE_11 0.8743, mean 0.8889).
- [x] 11. Slick-size quartile analysis present: `reports/slick_size_report.md`
      (TINY 0.9355 / SMALL 0.9547 / MEDIUM 0.9594 / LARGE 0.9678).
- [x] 12. Look-alike evaluation present: `reports/lookalike_report.md` (OIL 0.9583,
      LOOKALIKE 0.8145, CLEAN 0.0; rejection rate 0.30; clean false detection 0.0).
- [x] 13. Error taxonomy present: `reports/error_taxonomy.csv`
      (FP look-alike 7, neutral 7, boundary leakage 6).
- [x] 14. Slick geometry validation present: `reports/slick_geometry_report.md`
      (median area relative error ~4.3%).
- [x] 15. Cross-dataset external validation present: `reports/cross_dataset_results.csv`
      (Singapore Strait IoU 0.8487 / Dice 0.9181).
- [x] 16. Drift physics sanity tests PASS: `reports/drift_sanity_results.json`
      (eastward, northward, zero-forcing checks).
- [x] 17. Drift determinism verified: identical inputs -> identical origin + uncertainty.
- [x] 18. Drift sensitivity analysis run: 15 scenarios in `reports/drift_sensitivity.csv`.
- [x] 19. AIS data-quality audit clean: `reports/ais_quality_audit.csv` /
      `reports/ais_quality_report.md` (0 missing, 0 range, 0 duplicates, 0 large jumps).
- [x] 20. AIS trajectory validation PASS: `reports/ais_trajectory_validation.json`
      (east / north+gap / 90-degree turn, error ~0.112%).
- [x] 21. Explainability sanity suite run: `reports/explainability/sanity.json`.
- [x] 22. Randomization test outcome documented: WEAK (7396.24 vs 47763.59 energy) -
      attribution maps must not be over-interpreted.
- [x] 23. Perturbation test PASS documented: confidence drop ~0.055 on top-10% region.
- [x] 24. Attribution conclusion tiers implemented and tested:
      CANDIDATE_IDENTIFIED / INSUFFICIENT_EVIDENCE / NO_RELIABLE_CANDIDATE.
- [x] 25. Data Quality Service implemented and tested: per-source grades
      (satellite/model/environmental/drift/AIS) with strict worst-case overall.
- [x] 26. Evidence ledger with provenance implemented and tested
      (record types + status labels + Provenance schema).
- [x] 27. Low-confidence gating tested: LOW_CONFIDENCE detections flagged for
      analyst review with NO automatic attribution.
- [x] 28. Environment quality gate tested: FAIL env check blocks drift simulation
      (HTTP 422).
- [x] 29. Demo cases A-D + incident_complete available and tested via
      `POST /api/v1/demo/cases/{id}` (`backend/tests/test_demo_cases_and_ml.py`).
- [x] 30. Documentation updated: INVESTIGATION_WORKFLOW, DRIFT, AIS, ATTRIBUTION,
      EVIDENCE, DEMO, ML_EXPLAINABILITY_VALIDATION, QUALITY_GATE, README (encoding
      fixed), CURRENT_STATE (rewritten). No fabricated metrics; demo data labeled
      DEMO_DATA. **Secrets scan run** (see below) - no real credentials found.
- [x] 31. Final commit created and pushed to `origin` (`8f5a18d` on `main`,
      pushed as `59e46df..8f5a18d`; local and remote are in sync).

## Secrets Scan (verification note)

Scanned: the full tracked git tree plus `.env*` files and all tracked
`*.yaml`/`*.yml`/environment files for the patterns `api_key`, `password`,
`secret`, `token`, AWS-style keys, and private-key headers (excluding
`.venv/`, `node_modules/`, and the lockfile noise).

Findings:

- `.env.example` - only commented **placeholder** variables with empty values
  (`# POSTGRES_PASSWORD=postgres`, `# COPERNICUS_MARINE_PASSWORD=`,
  `# AIS_STREAM_API_KEY=`). No real secrets.
- `docker-compose.yml` - `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}`
  uses environment-variable interpolation with a local dev-only default; not a
  committed credential.
- `backend/app/core/config.py` - `CDS_API_KEY: str = ""` (empty default, no value).
- `frontend/package-lock.json` - the npm package name `js-tokens` is a
  false-positive match, not a credential.
- No `.env`, `.env.local`, or `.env.*.local` files exist in the working tree;
  `.env*` are gitignored and have not been committed.

Conclusion: no credentials or secrets were found in tracked files.

## Reference Commands

```bash
python -m pytest backend/tests -v
cd frontend && npx tsc --noEmit && npm run build
.venv/Scripts/python scripts/drift_sanity_tests.py
.venv/Scripts/python scripts/ais_audit.py
.venv/Scripts/python scripts/explain_sanity.py --model models/best_model/marinex_unet_v1.pt --sample patch_0101
git status            # verify working tree content before the final commit
git push origin       # pending until all [x] items above are satisfied
```