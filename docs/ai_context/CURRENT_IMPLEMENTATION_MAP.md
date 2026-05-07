# Current Implementation Map

Last verified against repo state: 2026-05-02, `HEAD` commit `53788d2`.

## Root

- `README.md`: minimal project summary.
- `REPO_STRUCTURE.md`: broad generated repository guide.
- `DEVELOPMENT_SETUP.md`: setup notes.
- `.dockerignore`: excludes git metadata, Python/Node caches, node modules, Expo output, runtime DB/output artifacts, raw/interim data, and generated `data/processed/background_load_15min.csv` from Docker build context.
- `Dockerfile.api`: Python 3.12 slim image for FastAPI/API and runtime CLI use; installs `requirements.txt`, sets `PYTHONPATH=/app:/app/packages/ev_core/src`, runs `uvicorn app.main:app` from `apps/api`.
- `Dockerfile.dashboard`: Python 3.12 slim image for Streamlit dashboard; installs `requirements.txt`, sets `PYTHONPATH`, runs `dashboards/sim_dashboard/app.py` on port 8501.
- `Dockerfile.mobile`: Node 22 Alpine build for Expo web export with `EXPO_PUBLIC_API_BASE_URL` build arg, served by nginx on port 80.
- `docker-compose.yml`: defines `runtime`, `api`, `dashboard`, and `mobile` services. Runtime/API/dashboard mount `./outputs/runtime` and `./data`; mobile builds with `EXPO_PUBLIC_API_BASE_URL: http://20.216.14.193:8000`.
- `requirements.txt`: root container dependency list for API/runtime/dashboard images.
- `config/`: placeholder/default YAML configuration. `config/env_config.yaml` references parquet paths that do not match the active CSV loader in `DundeeSimulationRepository`.

## API

- `apps/api/app/main.py`: creates the FastAPI app, reads comma-separated `CORS_ORIGINS` from the environment with local defaults, configures CORS, includes system, station, and recommendation routers.
- `apps/api/app/bootstrap_paths.py`: locates repo root and adds `packages/ev_core/src` plus repo root to `sys.path`.
- `apps/api/app/routers/recommendations.py`: defines `POST /recommendations`; calls `generate_recommendations`.
- `apps/api/app/services/recommendations_service.py`: thin wrapper over `inject_live_request`.
- `apps/api/app/services/runtime_service.py`: cached `RuntimeManager`, runtime-start guard, runtime state/events/recommendation accessors.
- `apps/api/app/schemas/recommendations.py`: aliases API schemas to `ev_core.contracts.requests.ExternalChargingRequest` and `ev_core.contracts.responses.RecommendationResponse`.
- `apps/api/app/routers/system.py`: root, health, runtime status/state/events/recent recommendations endpoints.
- `apps/api/app/routers/stations.py` and `apps/api/app/services/stations_service.py`: mock CRUD station API backed by `apps/api/app/mock_data.py`.

## Mobile

- `apps/mobile/src/screens/ChargingRequestScreen.tsx`: collects `targetSoc`, `preferenceMode`, and `chargerType`.
- `apps/mobile/src/screens/LoadingRecommendationsScreen.tsx`: calls `api.getRecommendations(request)`, navigates to results on success.
- `apps/mobile/src/services/api.ts`: builds the backend JSON payload and calls `POST /recommendations`; resolves `API_BASE_URL` from `process.env.EXPO_PUBLIC_API_BASE_URL` or local platform defaults.
- `apps/mobile/env.d.ts`: declares optional `process.env.EXPO_PUBLIC_API_BASE_URL` for TypeScript.
- `apps/mobile/src/types.ts`: defines mobile request/response types matching the current API response shape.
- `apps/mobile/src/screens/ResultsScreen.tsx`: maps `top_recommendation` and `alternatives` into UI cards.
- `apps/mobile/src/data/reservationStore.ts`: in-memory reservation state; not persisted through FastAPI.

## Runtime Service

- `services/sim_runtime/runtime_manager.py`
  - `RuntimeConfig`: default replay year, policy, runtime mode, loop interval, demand multiplier.
  - `RuntimeManager.__init__`: loads Dundee data bundle, creates `PlaceholderForecastProvider`, `RuntimeStorage`, and `EventBus`.
  - `RuntimeManager.start`: creates `DundeeEnv`, starts it, persists state, optionally warm-starts.
  - `RuntimeManager.tick`: advances environment and persists state.
  - `RuntimeManager.inject_request`: loads env from persisted state, validates/builds `ExternalChargingRequest`, injects it, gets ranked recommendations, saves request/recommendation/state.
  - `RuntimeManager.recommend`: produces recommendations without queuing the request.
  - `RuntimeManager.get_latest_state`, `get_recent_events`, `get_recent_recommendations`, `get_runtime_status`: storage-backed read APIs.
- `services/sim_runtime/storage.py`
  - `RuntimeArtifacts`: paths under `outputs/runtime`.
  - `RuntimeStorage`: JSON plus SQLite persistence for state, metrics, events, external requests, and recommendations.
- `services/sim_runtime/event_bus.py`: event bus; currently used with a no-op wildcard subscriber in `RuntimeManager`.
- `services/sim_runtime/demo.py`, `scripts/run_demo_runtime.py`, `scripts/inject_live_request.py`: runtime demo/helper entry points.

## EV Core

- `packages/ev_core/src/ev_core/contracts/requests.py`
  - `ExternalChargingRequest`: current live request contract.
  - `PreferenceMode`: `closest`, `cheapest`, `fastest`.
  - `SourceType`: `replay_background`, `synthetic_background`, `external_live`.
- `packages/ev_core/src/ev_core/contracts/responses.py`
  - `RecommendationOption`, `RecommendationResponse`.
  - `RequestSnapshot`, `StationStateSnapshot`, `TransformerStateSnapshot`, `MetricsSnapshot`, `StateSnapshot`.
- `packages/ev_core/src/ev_core/contracts/events.py`
  - `RuntimeEvent`.
- `packages/ev_core/src/ev_core/env/dundee_env.py`
  - `DundeeEnv`: request-driven simulator and current recommendation candidate builder.
- `packages/ev_core/src/ev_core/env/entities.py`
  - `Station`, `Transformer`, `SimulationRequest`, `ActiveChargingSession`, `GridContext`, `StationRuntimeState`.
- `packages/ev_core/src/ev_core/env/baselines.py`
  - Allocation policies: `RandomPolicy`, `GreedyFastestServicePolicy`, `OverloadAwarePolicy`, `CostAwarePolicy`.
- `packages/ev_core/src/ev_core/env/allocator.py`
  - `AllocationDecision`, `AllocationPolicy`.
- `packages/ev_core/src/ev_core/recommender/ranker.py`
  - `CandidateContext`, `RecommendationInput`, `CandidateRanker`, `WeightedHeuristicRanker`.
- `packages/ev_core/src/ev_core/recommender/service.py`
  - `RecommendationService`: calls ranker, assembles `RecommendationResponse`.
- `packages/ev_core/src/ev_core/data/repositories.py`
  - `DundeeDataPaths`, `DundeeDataBundle`, `DundeeSimulationRepository`.
- `packages/ev_core/src/ev_core/forecasting/provider.py`
  - `ForecastProvider`, `NullForecastProvider`, `PlaceholderForecastProvider`.

## Dashboard

- `dashboards/sim_dashboard/app.py`: Streamlit dashboard with runtime controls, map, live feed, recommendation panel, and metrics charts. It imports `RuntimeManager` and `RuntimeStorage` directly.

## Tests

No test files were found by repo-wide search for common test/spec paths and names. This should be treated as weak or missing coverage.
