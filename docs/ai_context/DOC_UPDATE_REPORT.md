# Doc Update Report

Last verified against repo state: 2026-05-02, `HEAD` commit `53788d2`.

## Update Summary

The delta since the previous documentation pass is deployment/configuration oriented. The repo added Dockerfiles, `docker-compose.yml`, root `requirements.txt`, `.dockerignore`, configurable API CORS origins, and a mobile `EXPO_PUBLIC_API_BASE_URL` override. No product-code changes were found in `packages/ev_core`, `services/sim_runtime`, dashboard data flow, recommendation ranking, candidate construction, runtime storage, request schemas, MARL/RL integration, or tests.

## Files Changed In Repo

Changed since docs commit `c463dc5`:

- `.dockerignore`: new Docker build-context exclusions.
- `Dockerfile.api`: new container image for FastAPI/API and runtime CLI base.
- `Dockerfile.dashboard`: new container image for Streamlit dashboard.
- `Dockerfile.mobile`: new Expo web build plus nginx serving image.
- `docker-compose.yml`: new multi-service deployment for runtime, API, dashboard, and mobile.
- `requirements.txt`: new root Python dependencies for container builds.
- `apps/api/app/main.py`: CORS origins now read from `CORS_ORIGINS`, with local defaults.
- `apps/mobile/env.d.ts`: new TypeScript declaration for `EXPO_PUBLIC_API_BASE_URL`.
- `apps/mobile/src/services/api.ts`: API base URL now uses `process.env.EXPO_PUBLIC_API_BASE_URL` before local platform defaults.

No changed files were found under:

- `packages/ev_core/`
- `services/sim_runtime/`
- `dashboards/`
- `data/`
- `config/`
- `scripts/`
- `outputs/`
- `docs/ai_context/` before this update

No `tests/` path exists in the current repo.

## Docs Updated

- `docs/ai_context/PROJECT_OVERVIEW.md`: added verification note and deployment/API URL/CORS facts.
- `docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md`: added root Docker/deployment files, updated `apps/api/app/main.py`, `apps/mobile/src/services/api.ts`, and `apps/mobile/env.d.ts`.
- `docs/ai_context/REQUEST_FLOW.md`: added verification note, mobile API base URL resolution, and API CORS env behavior.
- `docs/ai_context/NEXT_REFACTOR_PLAN.md`: added verification note and constraints to preserve deployed/mobile API URL and CORS behavior.
- `docs/ai_context/DOC_UPDATE_REPORT.md`: created this delta report.

Left unchanged because current code still matches existing documentation:

- `docs/ai_context/RECOMMENDER_FLOW.md`
- `docs/ai_context/RUNTIME_STATE_MAP.md`
- `docs/ai_context/DASHBOARD_FLOW.md`
- `docs/ai_context/DATA_ARTIFACTS_MAP.md`
- `docs/ai_context/OPEN_QUESTIONS.md`

## Current Repo Truth

- API/backend connection: `POST /recommendations` remains in `apps/api/app/routers/recommendations.py` and still delegates through `apps/api/app/services/recommendations_service.py` to `apps/api/app/services/runtime_service.py`.
- `ev_core` wiring: API schemas still alias `ExternalChargingRequest` and `RecommendationResponse`; runtime still uses `RuntimeManager` and `DundeeEnv`.
- Current recommender type: deterministic weighted heuristic ranking through `WeightedHeuristicRanker`; not mock-only, random, RL, or MARL.
- Baselines: simulator allocation baselines remain in `packages/ev_core/src/ev_core/env/baselines.py`; no new recommendation policy interface was added.
- MARL/RL status: no MARL/RL checkpoint inference, training, model-loading, or framework integration was found.
- Dashboard data flow: Streamlit dashboard still reads `RuntimeStorage` directly and imports `RuntimeManager`; it does not call FastAPI for panels.
- Tests: no test files or `tests/` directory were found.

## Contradictions Resolved

- Previous docs implied the mobile API URL was only platform-local with a comment for physical devices. Current code supports `EXPO_PUBLIC_API_BASE_URL`; docs now reflect that.
- Previous docs said API CORS used hard-coded local/LAN origins. Current code uses `CORS_ORIGINS` with local defaults; docs now reflect that.
- Previous docs did not mention deployment files. Current repo has Dockerfiles and compose wiring; docs now include them.

## Still Not Verified

- Container startup was not executed; whether `docker-compose.yml` successfully starts all services is not verified.
- The externally configured deployment IP in `docker-compose.yml` was not network-tested.
- Runtime boot in a clean container with mounted `data/` was not verified.
- Existing data concerns remain not verified here: parseability of `data/processed/station_capacity_assumptions.csv` and clean-checkout handling of missing `data/processed/background_load_15min.csv`.

## Recommended Next PR

Add characterization tests for `WeightedHeuristicRanker` and `RecommendationService`, then introduce a thin recommendation policy abstraction that wraps current weighted scoring without changing API/mobile/dashboard response shape.

## Do Not Do Yet

- Do not add MARL/RL checkpoint inference.
- Do not rename response fields.
- Do not change mobile/API/dashboard behavior.
- Do not migrate dashboard panels from direct storage reads to FastAPI yet.
- Do not extract candidate construction from `DundeeEnv` before tests lock down current behavior.
- Do not treat Docker deployment as proof that runtime recommendation behavior is correct without running verification.
