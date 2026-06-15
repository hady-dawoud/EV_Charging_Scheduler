# EV Smart Charging

Dundee-focused EV smart-charging monorepo for the EV-side smart charging prototype.

The repository combines a mobile app, FastAPI backend gateway, reusable EV simulator/recommender core, standalone simulator runtime, Streamlit dashboard, Docker deployment setup, and Dundee data-processing artifacts.

The current goal is to let a mobile charging request flow through the API into the simulator runtime, rank Dundee charging stations, return recommendation options, and expose runtime state in a dashboard.

## Deployed links

- [EV Mobile App](http://smartevcharging.uaenorth.cloudapp.azure.com/)
- [EV Simulator Dashboard](http://smartevcharging.uaenorth.cloudapp.azure.com/dashboard/)

## Current status

This repo is in a prototype and consolidation stage.

Implemented or partially implemented:

- Expo React Native mobile app for the user charging flow.
- FastAPI backend gateway.
- Mobile-backend recommendation integration.
- Shared request/response contracts in `packages/ev_core`.
- Dundee-grounded simulator inputs and station catalog.
- Standalone simulator runtime in `services/sim_runtime`.
- Streamlit simulator dashboard in `dashboards/sim_dashboard`.
- Runtime storage under `outputs/runtime`.
- Docker files and `docker-compose.yml` for containerized API, dashboard, runtime, and mobile web build.
- Nginx reverse-proxy deployment using the Azure VM DNS name.
- Release-signed Android APK `v0.1.2` for tester installs.

Current truth:

- `POST /recommendations` exists and injects a live external charging request into the simulator runtime.
- The mobile app calls the backend through the deployed `/api` reverse-proxy path.
- The recommended Android tester build is GitHub Release `v0.1.2`, asset `ev-smart-charging-v0.1.2.apk`.
- The `v0.1.2` APK is release-signed, verified with `apksigner`, and uses Android `versionCode 3` / `versionName "0.1.2"`.
- `v0.1.0` and `v0.1.1` are older APK releases and should not be recommended to testers.
- The default recommendation policy remains deterministic `weighted_score`.
- PR 6.2 adds opt-in feeder-checkpoint safety wrappers around the existing
  closest, cheapest, fastest, weighted, and request-preference rankers.
- The feeder checkpoint is advisory only: it can apply a bounded penalty or
  block unsafe candidates, but it does not replace the final preference ranker.
- Federated Learning is not part of the active implementation direction.
- Station CRUD endpoints still use mock in-memory station data.
- Full production database persistence is not implemented yet.
- The deployed system is a working prototype, not a production-ready platform.

## High-level architecture

```text
Mobile App
   |
   v
FastAPI Backend/API
   |
   v
Simulator Runtime
   |
   v
EV Core: contracts, Dundee environment, recommender, baselines
   |
   +--> Runtime outputs / recommendation history
   |
   +--> Streamlit Dashboard
```

## Repository layout

```text
apps/
  api/                     FastAPI gateway used by the mobile app
  mobile/                  Expo React Native mobile application

packages/
  ev_core/                 Shared EV contracts, simulator environment, recommender logic,
                           baseline policies, data loaders, and utilities

services/
  sim_runtime/             Standalone runtime manager, event bus, persistence, and demo control

dashboards/
  sim_dashboard/           Streamlit dashboard for simulator/runtime visibility

data/
  raw/                     Raw source datasets, including Dundee charging sessions
  interim/                 Cleaned/model-ready intermediate data
  processed/               Station catalog, topology, replay inputs, prices, load, PV, etc.

outputs/
  qc/                      Quality reports and generated analysis outputs
  figures/                 Generated figures
  maps/                    Generated maps
  runtime/                 Runtime database, latest state, metrics, events, and samples

scripts/                   Data-building and runtime helper scripts
config/                    Configuration files

docs/                      Project notes and handoff context
```

## Main components

### Mobile app

Located in `apps/mobile`.

The app is the user-facing prototype. It supports the charging request and recommendation flow, including target SOC, preference mode, charger type, recommendations, station details, reservation confirmation, sessions, and profile screens.

The app should stay user-facing and should not expose simulator internals directly.

The deployed mobile app is available at:

```text
http://smartevcharging.uaenorth.cloudapp.azure.com/
```

Recommended Android tester APK:

```text
GitHub Release: v0.1.2
Asset: ev-smart-charging-v0.1.2.apk
SHA256: EA8D2091694329FF4E6836EB269694AC2A6EBCEBC903C2747320E4F20E1BD99B
Android versionCode: 3
Android versionName: 0.1.2
```

Use `docs/android_release_runbook.md` for release verification and publishing notes. Do not commit APK files, `release-artifacts/`, build outputs, private keystores, Gradle signing secrets, or local secret files.

### Backend/API gateway

Located in `apps/api`.

The backend is a FastAPI service that receives mobile requests, validates them through shared contracts, calls runtime/recommendation logic, and returns ranked charging options.

Important endpoints include:

- `GET /`
- `GET /health`
- `GET /runtime/status`
- `GET /runtime/state`
- `GET /runtime/events`
- `GET /runtime/recommendations/recent`
- `GET /stations`
- `GET /stations/{station_id}`
- `POST /stations`
- `PUT /stations/{station_id}`
- `DELETE /stations/{station_id}`
- `POST /recommendations`

The API is configured for the `/api` deployment prefix behind Nginx:

```python
FastAPI(root_path="/api")
```

### Backend database / persistence

A full production backend database is not implemented yet.

Current persistence is runtime-oriented and stored under:

```text
outputs/runtime
```

Runtime outputs include:

- latest state,
- latest metrics,
- recent recommendations,
- external requests,
- event log,
- runtime status/config files,
- runtime SQLite database,
- sample request/response contracts.

Current station CRUD still uses mock in-memory data. Production persistence for users, reservations, sessions, and long-term station state remains future work.

Runtime-generated files should not be treated as source files and should generally be ignored in Git.

Recommended `.gitignore` entries:

```gitignore
outputs/runtime/
outputs/runtime/*.json
outputs/runtime/*.jsonl
outputs/runtime/*.db
```

### Mobile-backend integration

The mobile-backend integration is currently active.

Current live recommendation path:

```text
Mobile request JSON
  -> FastAPI POST /api/recommendations
  -> ExternalChargingRequest contract
  -> simulator runtime injection
  -> Dundee station candidate ranking
  -> RecommendationResponse
  -> mobile recommendations screen
  -> runtime/dashboard history
```

The request should preserve a stable `client_request_id` where possible. This lets the runtime and dashboard identify mobile-originated live requests during demos.

### EV core package

Located in `packages/ev_core`.

This package contains reusable logic for:

- request/response/event contracts,
- Dundee simulator environment,
- station and runtime entities,
- deterministic baseline policies,
- optional feeder checkpoint inference and RL safety wrapper policies,
- recommendation ranking,
- data repositories/loaders,
- forecasting interfaces,
- and time utilities.

The default recommender is still the deterministic weighted heuristic baseline.
Hybrid RL safety policies are opt-in and keep the existing deterministic
preference ranker as the final ordering rule. See
`docs/ev_side/PR_6_2_RL_SAFETY_RUNTIME_RUNBOOK.md` for artifacts,
configuration, evidence boundaries, and verification commands.

### Simulator runtime

Located in `services/sim_runtime`.

The runtime wraps the Dundee environment, manages simulator state, stores runtime artifacts, supports live request injection, and exposes state for the API and dashboard.

Runtime outputs are written under `outputs/runtime`.

The runtime is required for live recommendations. If the runtime has not started, the API can return an error saying the simulator runtime must be started first.

### Dashboard

Located in `dashboards/sim_dashboard`.

The dashboard is separate from the mobile app. It is used for simulation/demo visibility, including runtime state, requests, recommendations, metrics, and event history.

Deployed dashboard:

```text
http://smartevcharging.uaenorth.cloudapp.azure.com/dashboard/
```

### Dundee data and simulator inputs

The V1 simulator is grounded in Dundee public charging-session data.

Current modeling assumptions:

- each unique Dundee `Site` is treated as one station,
- each unique Dundee `CP ID` is treated as a chargepoint/port proxy,
- all 35 Dundee stations are included,
- 90 CP IDs are used as chargepoint proxies,
- zones and transformers are synthetic but documented,
- simulator time resolution is 15 minutes.

Key data artifacts include:

- cleaned Dundee sessions,
- model-ready Dundee sessions,
- station and chargepoint catalogs,
- station geolocation outputs,
- 4-zone / 8-transformer topology overlays,
- 2023 and 2024 request replay tables,
- price, PV, and background-load time series.

Large generated artifacts should not be committed to normal Git if they exceed practical repository limits. Prefer committing scripts, configs, contracts, small samples, and docs, then regenerating large processed outputs locally or sharing them separately.

## Local setup

### Python environment

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If working only inside `apps/api`, the API also has its own `pyproject.toml` and local setup notes.

### Start the simulator runtime

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m services.sim_runtime.main start --day 2024-06-10 --policy overload_aware
```

Advance the runtime manually:

```powershell
.\.venv\Scripts\python.exe -m services.sim_runtime.main tick --steps 4
```

Inspect runtime state:

```powershell
.\.venv\Scripts\python.exe -m services.sim_runtime.main state
```

Run a short demo:

```powershell
.\.venv\Scripts\python.exe scripts\run_demo_runtime.py --day 2024-06-10 --ticks 4
```

Inject a sample live request:

```powershell
.\.venv\Scripts\python.exe scripts\inject_live_request.py --sample
```

### Start the API locally

From `apps/api`:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful local URLs:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

The API reads several optional environment variables:

- `CORS_ORIGINS`
- `RECOMMENDATION_POLICY_NAME`
- `TOPOLOGY_SCENARIO_ID`
- `DYNAMIC_PRICING_ENABLED`
- `ROUTING_PROVIDER_NAME`
- `OSMNX_GRAPH_PATH`

### Start the dashboard locally

From the repository root:

```powershell
.\.venv\Scripts\streamlit.exe run dashboards\sim_dashboard\app.py --server.headless true --server.port 8501
```

Open:

```text
http://127.0.0.1:8501
```

### Start the mobile app locally

From `apps/mobile`:

```powershell
npm install --legacy-peer-deps
npx expo start
```

For local web/API testing, set the API base URL as needed:

```powershell
$env:EXPO_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
```

For deployed reverse-proxy testing, use:

```powershell
$env:EXPO_PUBLIC_API_BASE_URL="http://smartevcharging.uaenorth.cloudapp.azure.com/api"
```

Use an `/api` suffix only when the deployment/reverse-proxy setup expects it.

## Docker setup

The repo includes Dockerfiles for:

- API: `Dockerfile.api`
- dashboard: `Dockerfile.dashboard`
- mobile web build: `Dockerfile.mobile`

Strict feeder RL deployment uses Git LFS for the three feeder parquet files
and the final feeder checkpoint. Materialize and validate them before building:

```powershell
git lfs install
git lfs pull
python scripts\verification\check_deployment_artifacts.py --json
uv run --with pandas --with pyarrow python scripts\verification\check_deployment_artifacts.py --json --check-parquet
```

Create a local environment file from the secret-free template:

```powershell
Copy-Item .env.example .env
```

Compose uses the `postgres` service name inside containers, mounts the feeder
data and final checkpoint read-only, enables strict no-fallback RL safety by
default, and builds the mobile web app against `http://localhost:8000`.

Run the stack with:

```powershell
docker compose up --build
```

Or in detached mode:

```powershell
docker compose up -d --build
```

Typical exposed ports:

- API: `8000`
- dashboard: `8501`
- mobile web: `3000`

Current deployed routing through Nginx:

```text
http://smartevcharging.uaenorth.cloudapp.azure.com/           -> mobile app
http://smartevcharging.uaenorth.cloudapp.azure.com/api/       -> FastAPI backend
http://smartevcharging.uaenorth.cloudapp.azure.com/dashboard/ -> Streamlit dashboard
```

## Recommendation flow

Current live recommendation path:

```text
Mobile request JSON
  -> FastAPI POST /api/recommendations
  -> ExternalChargingRequest contract
  -> simulator runtime injection
  -> Dundee station candidate ranking
  -> RecommendationResponse
  -> mobile recommendations screen
  -> runtime/dashboard history
```

The default recommendation output is deterministic weighted heuristic scoring.
When explicitly enabled, the PR 6.2 hybrid path builds feeder context, runs the
checkpoint, maps candidates, applies bounded safety filtering, and then
preserves the selected deterministic preference ranker. The response schema and
raw distance, duration, cost, pricing, queue, utilization, and headroom fields
remain unchanged.

## Current limitations

- Recommendation scoring is deterministic heuristic ranking, not learned MARL inference yet.
- Station CRUD still uses mock in-memory data.
- Full production database persistence is not implemented yet.
- Reservation persistence is not complete.
- Runtime/demo behavior may still feel static unless the simulator is advanced manually or started in a busier scenario.
- Continuous ticking, replay-background event emission, warm-start, and hybrid request-source modes still need more polish.
- Some Dundee station coordinates still need verification for stronger map/navigation realism.
- Forecasting is behind interfaces and is not the current implemented core.

## Roadmap

Near-term:

1. Keep mobile API calls routed through `/api`.
2. Keep Docker and Nginx deployment paths stable.
3. Make runtime demo behavior more live with continuous ticking and better event emission.
4. Improve dashboard auto-refresh and recent-event visibility.
5. Stabilize replay, synthetic, and hybrid request-source modes.
6. Freeze `ExternalChargingRequest` and `RecommendationResponse` contracts.
7. Keep the existing weighted heuristic recommender as a documented baseline policy.
8. Improve backend/app integration while preserving the current response shape.
9. Add stronger tests around recommendation ranking and runtime state transitions.
10. Replace mock/in-memory station and reservation persistence with a real database layer.

Later:

1. Add MARL training and evaluation against deterministic baselines.
2. Introduce MARL checkpoint inference behind a clean ranker/policy interface.
3. Replace remaining mock station/session persistence with production-ready storage.
4. Continue improving Dundee topology, routing, and map realism.

## Development principles

- Keep simulator, data pipeline, runtime, and app layers modular.
- Do not couple mobile UI directly to simulator internals.
- Do not reintroduce Federated Learning as the active project core unless the project direction explicitly changes.
- Treat Dundee as the V1 real-world station/session anchor.
- Treat synthetic zones/transformers as documented simulator assumptions, not real utility topology.
- Keep deterministic baselines before trusting learned policies.
- Commit source code, configs, contracts, small samples, and docs.
- Avoid committing huge regenerated data artifacts.
- Ignore runtime-generated files under `outputs/runtime`.
