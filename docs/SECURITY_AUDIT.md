# MARINeX Security Audit (SIH26143)

| | |
|---|---|
| **Date** | 2026-09-10 (final validation phase) |
| **Scope** | tracked source, dependency manifests, build output, runtime defaults |
| **Result** | **PASS** — no secrets in repository; no applicable high-severity advisories; no credentials embedded in bundles |

## 1. Repository hygiene

- `git ls-files` sensitive filter: only `.env.example` matches `.env*`; **no** `.env`, `*.db`, `*.pem`,
  `*.p12`, `*.key`, credential, or secret files are tracked (762 tracked files scanned).
- Pattern scan over `*.py`, `*.ts`, `*.tsx`, `*.json`, `*.yaml`, `*.yml`, `*.toml` for
  `password=/api_key=/secret_key=/BEGIN * PRIVATE` literals: **0 matches**.
- `backend/.env.example` inspected: contains only placeholders and commented defaults
  (SQLite URL, attribution weights, drift factors, optional Copernicus/AIS placeholders).

## 2. Frontend dependency audit

- `npm audit --omit=dev --audit-level=high`: **2 moderate** vulnerabilities.
- Advisory GHSA-337j-9hxr-rhxg (react-router / react-router-dom SSR-hydration arbitrary
  constructor injection) — **NOT applicable**: MARINeX frontend is a **pure client-side SPA**
  (Vite build, no SSR/SSG renderer, no server hydration path; see `vite.config.ts`).
- Fix path exists (`react-router-dom@7.18.3`) but is a breaking major change; deliberately
  deferred to keep the reproducible frozen build (`react-router-dom@^6.29.0`) — documentation
  of the residual low risk is preferred over an unreviewed forced major upgrade during final
  validation.

## 3. Backend & API hygiene

- SQLAlchemy ORM with bound parameters only (no string-interpolated SQL in services).
- Request bodies validated with Pydantic schemas; demo incident endpoints tested
  (backend suite 35/35 green; ML suite 19/19).
- CORS/proxy: frontend dev proxy targets `http://localhost:8000` with `changeOrigin`; no
  external hosts, no embedded tokens.
- No production credentials required: authentication is not part of this project's scope;
  the demo scenario runs on local SQLite (`sqlite:///./marinex.db`).
- SQLite files are gitignored; the stale dev DB was rebuilt from the current schema
  (seed `scripts/seed_demo_data.py`) rather than patched.

## 4. Build artifacts

- Frontend build (`npm run build`, `dist/`) contains no `.env`, keys, or URLs other than
  same-host `/api` relative calls. No analytics/external beacon scripts.

## 5. Residual risks (accepted, documented)

1. `react-router-dom` moderate advisory — N/A for SPA; revisit on next dependency bump.
2. Python/C++ dependency CVEs not machine-checked offline; pins are exact in `requirements*.txt`.
3. No inbound authentication/authorization (out of scope for the SIH demo; documented for
   deployment).

## Evidence / commands

- `git ls-files` + pattern grep; `npm audit --omit=dev`; `npm run build`; backend + ML pytest runs.
- Logged in this doc on 2026-09-10 during the final validation phase.