# Repository Structure

This repository is an EV smart charging monorepo. It combines a mocked mobile/API
prototype with a newer Dundee-focused simulator, data-processing pipeline,
runtime service, and dashboard.

## High-Level Architecture

- `apps/mobile` is an Expo React Native app for the user-facing EV charging flow.
- `apps/api` is a FastAPI gateway. It still has simple in-memory station CRUD,
  but its recommendation endpoint now calls the standalone simulator runtime.
- `packages/ev_core` is the reusable Python core for contracts, Dundee simulator
  state, recommendation ranking, data repositories, forecasting interfaces, and
  utility code.
- `services/sim_runtime` is a standalone runtime manager and CLI around
  `ev_core.env.DundeeEnv`.
- `dashboards/sim_dashboard` is a Streamlit dashboard over the runtime artifacts.
- `scripts` contains one-off and repeatable data-building jobs for Dundee raw
  sessions, QC outputs, station catalogs, topology, simulator replay inputs, and
  runtime contract samples.
- `data` stores raw Dundee session CSVs plus processed/interim simulator inputs.
- `outputs` stores generated plots, maps, QC reports, and runtime state/history.
- `config` contains placeholder/default YAML configuration for future data and
  simulation workflows.
- `notebooks` contains exploratory notebooks and design notes.

## Directory Map

```text
.
|-- apps/
|   |-- api/                 FastAPI prototype and runtime integration layer
|   `-- mobile/              Expo React Native mobile client
|-- config/                  YAML source registry and simulator defaults
|-- dashboards/
|   `-- sim_dashboard/       Streamlit runtime dashboard
|-- data/
|   |-- raw/                 Original source data placeholders and Dundee CSVs
|   |-- interim/             Cleaned/model-ready Dundee parquet artifacts
|   `-- processed/           Station, topology, replay, price, and PV artifacts
|-- notebooks/               Exploratory/design notebooks
|-- outputs/
|   |-- figures/             Static PNG plots
|   |-- maps/                Interactive HTML maps
|   |-- qc/                  Generated quality/replay/topology notes
|   `-- runtime/             Runtime JSON, JSONL, SQLite, and sample contracts
|-- packages/
|   `-- ev_core/             Shared Python package for simulator/recommender code
|-- scripts/                 Data-building and runtime helper scripts
`-- services/
    `-- sim_runtime/         Standalone Dundee simulator service/CLI
```

## Root Files

| File | Contents |
| --- | --- |
| `.gitattributes` | Marks `data/interim/*.csv` for Git LFS. |
| `.gitignore` | Ignores OS files, envs, Node/Python build artifacts, generated interim CSVs, generated background-load CSV, and runtime outputs. |
| `README.md` | Minimal project description: mobile app, backend API/database, integration, and federated-learning flow are planned/current parts. |
| `DEVELOPMENT_SETUP.md` | Explains the separation between app prototypes and newer EV-core/data scaffolding, plus suggested `uv` setup. |
| `REPO_STRUCTURE.md` | This generated repository guide. |

## Apps

### `apps/`

| File | Contents |
| --- | --- |
| `apps/README.md` | Empty placeholder. |

### `apps/api`

The API is a FastAPI app with CORS enabled for local Expo development. It exposes
health/runtime endpoints, station CRUD against mock memory data, and a live
recommendation endpoint backed by `services.sim_runtime.RuntimeManager`.

| File | Contents |
| --- | --- |
| `apps/api/.gitignore` | Empty placeholder. |
| `apps/api/README.md` | Local FastAPI setup and useful URLs. |
| `apps/api/pyproject.toml` | API package metadata and dependencies: FastAPI, Uvicorn, Pydantic, pandas, pyarrow, Streamlit packages. |
| `apps/api/uv.lock` | Locked Python dependency graph for the API environment. |
| `apps/api/app/__init__.py` | Empty package initializer. |
| `apps/api/app/main.py` | Creates the FastAPI app, configures CORS, and includes system, stations, and recommendations routers. |
| `apps/api/app/api_responses.py` | Small helpers for OpenAPI 404/400 error response metadata. |
| `apps/api/app/bootstrap_paths.py` | Locates the repo root and inserts `packages/ev_core/src` plus the repo root into `sys.path`. |
| `apps/api/app/mock_data.py` | Two in-memory mock stations: Station A in Cairo and Station B in Nasr City. |
| `apps/api/app/routers/stations.py` | `GET/POST/PUT/DELETE /stations` endpoints over the mock station store. |
| `apps/api/app/routers/recommendations.py` | `POST /recommendations`; injects an external charging request into the simulator runtime and returns a recommendation response. |
| `apps/api/app/routers/system.py` | Root, health, runtime status, runtime state, recent events, and recent recommendations endpoints. |
| `apps/api/app/schemas/__init__.py` | Re-exports API schemas. |
| `apps/api/app/schemas/errors.py` | `ErrorResponse` Pydantic model. |
| `apps/api/app/schemas/stations.py` | Station CRUD Pydantic models and list response model. |
| `apps/api/app/schemas/recommendations.py` | Aliases API recommendation request/response models to `ev_core` contracts. |
| `apps/api/app/services/stations_service.py` | In-memory station listing, filtering, create, update, and delete logic. |
| `apps/api/app/services/recommendations_service.py` | Thin wrapper that forwards recommendation requests to runtime injection. |
| `apps/api/app/services/runtime_service.py` | Cached `RuntimeManager` access and guard helpers for runtime state, events, and recommendations. |

### `apps/mobile`

The mobile app is an Expo React Native app with dark/neon styling. It has login,
signup, home, charging-request, recommendation loading, results, station details,
reservation confirmation, sessions, and profile screens.

| File | Contents |
| --- | --- |
| `apps/mobile/.gitignore` | Ignores Expo/Node build output, env files, and generated Expo type files. |
| `apps/mobile/README.md` | Minimal `# Mobile App` placeholder. |
| `apps/mobile/package.json` | Expo app metadata, scripts, React Native/navigation/lucide dependencies, and TypeScript dev dependency. |
| `apps/mobile/package-lock.json` | Locked npm dependency graph. |
| `apps/mobile/app.json` | Expo app config: `evMock`, portrait, dark UI, splash/adaptive icon colors. |
| `apps/mobile/babel.config.js` | Uses `babel-preset-expo`. |
| `apps/mobile/tsconfig.json` | Extends Expo TypeScript config, enables strict mode and `react-jsx`. |
| `apps/mobile/App.tsx` | Root navigation container and native stack: Splash, Login, Signup, Main tabs, request/loading/results/details/confirm flows. |
| `apps/mobile/src/theme.ts` | Shared colors, spacing, radii, glass styles, and web-only CSS shadow/blur helpers. |
| `apps/mobile/src/types.ts` | User, vehicle, station, session, recommendation, reservation, and navigation route types. |
| `apps/mobile/src/services/api.ts` | Mock login/session/reservation APIs plus real `POST /recommendations` call to the FastAPI backend. |
| `apps/mobile/src/data/mockData.ts` | Mock user, vehicle, Cairo station examples, and sample sessions. |
| `apps/mobile/src/data/reservationStore.ts` | In-memory current/past reservation store for the app session. |
| `apps/mobile/src/components/MainTabs.tsx` | Bottom tab navigator for Home, Sessions, and Profile. |
| `apps/mobile/src/screens/SplashScreen.tsx` | Animated landing screen with login/signup entry points. |
| `apps/mobile/src/screens/LoginScreen.tsx` | Login form with mock API login and password visibility toggle. |
| `apps/mobile/src/screens/SignupScreen.tsx` | Signup form with mock delay before entering the main app. |
| `apps/mobile/src/screens/HomeScreen.tsx` | Vehicle status dashboard with battery/range display and charging request CTA. |
| `apps/mobile/src/screens/ChargingRequestScreen.tsx` | Lets the user pick target SOC, optimization preference, and charger type. |
| `apps/mobile/src/screens/LoadingRecommendationsScreen.tsx` | Animated loading state that calls `api.getRecommendations`; navigates to results or shows an error. |
| `apps/mobile/src/screens/ResultsScreen.tsx` | Maps API recommendation options into UI cards and links to station details. |
| `apps/mobile/src/screens/StationDetailsScreen.tsx` | Detail view for a recommended station, with fallback demo station data. |
| `apps/mobile/src/screens/ReservationConfirmScreen.tsx` | Saves a reservation into the in-memory store and shows confirmation details. |
| `apps/mobile/src/screens/SessionsScreen.tsx` | Shows current and past reservations from `reservationStore`. |
| `apps/mobile/src/screens/ProfileScreen.tsx` | User/vehicle profile and static settings menu. |

## Config

| File | Contents |
| --- | --- |
| `config/data_sources.yaml` | Placeholder registry for Dundee, ACN, and external raw data paths plus interim/processed targets. |
| `config/env_config.yaml` | Placeholder standalone environment config: 15-minute UTC time base, 96-step horizon, asset paths. Note: it references parquet station/topology paths, while current processed artifacts are CSV. |
| `config/simulation_defaults.yaml` | Placeholder simulation defaults: seed, 96-step horizon, baseline policy, dummy forecast provider, optional PV disabled. |

## Dashboards

| File | Contents |
| --- | --- |
| `dashboards/__init__.py` | Package marker for dashboard code. |
| `dashboards/sim_dashboard/__init__.py` | Package marker for the simulator dashboard. |
| `dashboards/sim_dashboard/README.md` | Explains that the dashboard reads standalone runtime artifacts under `outputs/runtime`. |
| `dashboards/sim_dashboard/pyproject.toml` | Dashboard package metadata and dependencies: `ev-core`, Streamlit, pandas, Altair. |
| `dashboards/sim_dashboard/app.py` | Streamlit dashboard with runtime controls, status display, station/transformer maps, metrics, recommendation tables, external requests, events, and arrival charts. |

## Services

### `services/`

| File | Contents |
| --- | --- |
| `services/__init__.py` | Package marker for standalone services. |

### `services/sim_runtime`

This service wraps `DundeeEnv` with persistence, CLI commands, demo presets, and
local event handling. It stores JSON/JSONL/SQLite artifacts under
`outputs/runtime`.

| File | Contents |
| --- | --- |
| `services/sim_runtime/__init__.py` | Re-exports `RuntimeManager`. |
| `services/sim_runtime/README.md` | Describes the standalone Dundee simulator runtime and its separation from `apps/**`. |
| `services/sim_runtime/pyproject.toml` | Runtime package metadata and dependencies: `ev-core`, pandas, Pydantic. |
| `services/sim_runtime/bootstrap_paths.py` | Same repo-root/path bootstrap pattern used by the API. |
| `services/sim_runtime/demo.py` | Sample external charging request and Busy Afternoon demo preset helpers. |
| `services/sim_runtime/event_bus.py` | In-process pub/sub event bus for `RuntimeEvent` handlers. |
| `services/sim_runtime/main.py` | CLI with `start`, `reset`, `tick`, `pause`, `stop-loop`, `state`, `metrics`, `status`, and `inject` commands. |
| `services/sim_runtime/runtime_manager.py` | Main runtime orchestrator: loads Dundee data, starts/resets/ticks/loops envs, injects requests, recommends, persists status/state/events. |
| `services/sim_runtime/storage.py` | JSON plus SQLite persistence for state, metrics, events, recommendations, external requests, and runtime status. |

## Shared Python Package: `packages/ev_core`

| File | Contents |
| --- | --- |
| `packages/ev_core/pyproject.toml` | `ev-core` package metadata and dependencies for data, notebooks, simulation, testing, and linting. |
| `packages/ev_core/README.md` | Not readable as Markdown; the file contains binary-looking bytes. It appears corrupted or mislabeled. |
| `packages/ev_core/src/ev_core/__init__.py` | Top-level package exports. |

### Contracts

| File | Contents |
| --- | --- |
| `packages/ev_core/src/ev_core/contracts/__init__.py` | Re-exports request, response, event, and schema contract models. |
| `packages/ev_core/src/ev_core/contracts/types.py` | NewType aliases for station/connector/vehicle/request/time-step IDs and fixed 15-minute resolution literal. |
| `packages/ev_core/src/ev_core/contracts/requests.py` | `ExternalChargingRequest` model; validates timestamps, infers requested energy from SOC/battery when needed. |
| `packages/ev_core/src/ev_core/contracts/responses.py` | Recommendation option/response models plus request, station, transformer, metrics, and full runtime state snapshots. |
| `packages/ev_core/src/ev_core/contracts/events.py` | `RuntimeEvent` model with summary/message normalization. |
| `packages/ev_core/src/ev_core/contracts/schemas.py` | Older/shared placeholder schemas for time windows, charging requests, station snapshots, and recommendation candidates. |

### Data

| File | Contents |
| --- | --- |
| `packages/ev_core/src/ev_core/data/__init__.py` | Re-exports data helper classes. |
| `packages/ev_core/src/ev_core/data/io.py` | Minimal pandas CSV read/write helpers with parent directory creation on write. |
| `packages/ev_core/src/ev_core/data/cleaning.py` | Placeholder `CleaningContext` and unimplemented `clean_frame`. |
| `packages/ev_core/src/ev_core/data/feature_builders.py` | Placeholder `FeatureBuilderSpec` and unimplemented `build_features`. |
| `packages/ev_core/src/ev_core/data/repositories.py` | Filesystem dataset handles plus `DundeeSimulationRepository`, which loads processed Dundee artifacts and can derive fallback replay/background/price/PV data. |

### Environment

| File | Contents |
| --- | --- |
| `packages/ev_core/src/ev_core/env/__init__.py` | Re-exports simulator environment classes and policies. |
| `packages/ev_core/src/ev_core/env/allocator.py` | Allocation decision dataclass and policy protocol. |
| `packages/ev_core/src/ev_core/env/baselines.py` | Baseline policies: stable random, greedy fastest service, overload-aware, cost-aware, and policy registry. |
| `packages/ev_core/src/ev_core/env/entities.py` | Dataclasses for connectors, stations, transformers, simulation requests, active sessions, grid context, and mutable station runtime state. |
| `packages/ev_core/src/ev_core/env/environment.py` | Base simulation environment interface and `StepResult`. |
| `packages/ev_core/src/ev_core/env/reward.py` | Reward breakdown dataclass and placeholder reward model. |
| `packages/ev_core/src/ev_core/env/dundee_env.py` | Main Dundee request-driven simulator. Handles reset/restore/start/pause, replay/synthetic/external request activation, recommendation ranking, allocation, queues, sessions, transformer load/headroom, events, and state snapshots. |

### Forecasting

| File | Contents |
| --- | --- |
| `packages/ev_core/src/ev_core/forecasting/__init__.py` | Forecasting exports. |
| `packages/ev_core/src/ev_core/forecasting/provider.py` | Forecast request/series models, provider protocol, zero-valued provider, and table-backed placeholder provider. |
| `packages/ev_core/src/ev_core/forecasting/dummy_provider.py` | Backward-compatible dummy provider subclassing the null provider. |

### Recommender

| File | Contents |
| --- | --- |
| `packages/ev_core/src/ev_core/recommender/__init__.py` | Recommender exports. |
| `packages/ev_core/src/ev_core/recommender/ranker.py` | Candidate context/input models and weighted heuristic ranker for closest/cheapest/fastest preferences. |
| `packages/ev_core/src/ev_core/recommender/service.py` | Recommendation orchestration service that returns top option, alternatives, congestion note, and debug summary. |

### Utils

| File | Contents |
| --- | --- |
| `packages/ev_core/src/ev_core/utils/__init__.py` | Utility exports. |
| `packages/ev_core/src/ev_core/utils/logging.py` | Simple logger factory. |
| `packages/ev_core/src/ev_core/utils/timebase.py` | 15-minute time-base helpers: floor, ceil, advance, and minute differences. |

## Scripts

| File | Contents |
| --- | --- |
| `scripts/clean_dundee.py` | Cleans raw Dundee annual session CSVs into unified interim clean CSV/parquet columns. |
| `scripts/clean_acn.py` | Placeholder ACN cleaning entry point; parses input/output args but does not implement cleaning. |
| `scripts/build_dundee_qc_and_plots.py` | Builds QC flags, model-ready Dundee dataset, reconstructed load, summary CSV/Markdown, and static plots/maps. |
| `scripts/build_dundee_station_catalog.py` | Builds Dundee station, charge point, location seed, station master, and GeoJSON catalogs from cleaned sessions. |
| `scripts/build_dundee_spatial_topology.py` | Builds verified station locations, zone map, transformer map, station capacity assumptions, zones, transformers, topology maps, and design notes. |
| `scripts/build_dundee_simulator_inputs.py` | Builds request replay tables for 2023/2024, request-generator priors, deterministic 15-minute price/PV/background assumptions, and replay summaries. |
| `scripts/build_dundee_interactive_maps.py` | Builds interactive Dundee station/topology maps and visual review assets around daily energy checks. |
| `scripts/build_background_load_15min.py` | Placeholder entry point for background-load table generation. |
| `scripts/build_optional_pv_tables.py` | Placeholder entry point for optional PV feature tables. |
| `scripts/build_price_15min.py` | Placeholder entry point for 15-minute price tables. |
| `scripts/build_request_seed_table.py` | Placeholder entry point for request seed table generation. |
| `scripts/build_station_master.py` | Placeholder entry point for station master table generation. |
| `scripts/build_transformer_station_map.py` | Placeholder entry point for transformer-to-station mapping. |
| `scripts/run_demo_runtime.py` | Starts a short Dundee runtime demo and prints the latest state. |
| `scripts/inject_live_request.py` | Injects a sample or supplied JSON payload into the runtime and prints recommendations. |
| `scripts/export_sample_contracts.py` | Writes sample external request, recommendation response, and manifest JSON files to `outputs/runtime`. |

## Data

### Raw Data

| File | Contents |
| --- | --- |
| `data/raw/acn/.gitkeep` | Keeps the empty ACN raw-data placeholder directory. |
| `data/raw/external/.gitkeep` | Keeps the empty external raw-data placeholder directory. |
| `data/raw/dundee/.gitkeep` | Keeps the Dundee raw-data directory. |
| `data/raw/dundee/dundee_sessions_2021_h2.csv` | Raw Dundee session export, 35,871 rows. Columns: `SDR ID`, `Site`, `CP ID`, `Connector Type`, `Consum(kWh)`, `Duration`, `Start`, `End`, `Postcode`. |
| `data/raw/dundee/dundee_sessions_2022.csv` | Raw Dundee session export, 88,145 rows with the same raw columns. |
| `data/raw/dundee/dundee_sessions_2023.csv` | Raw Dundee session export, 119,065 rows with the same raw columns. |
| `data/raw/dundee/dundee_sessions_2024.csv` | Raw Dundee session export, 94,661 rows with the same raw columns. |
| `data/raw/dundee/dundee_sessions_2025_ytd.csv` | Raw Dundee session export, 50,101 rows with the same raw columns. |

### Interim Data

| File | Contents |
| --- | --- |
| `data/interim/.gitignore` | Ignores interim CSV outputs and `.gitattributes` in this directory. |
| `data/interim/.gitkeep` | Keeps the interim directory. |
| `data/interim/dundee_sessions_clean.parquet` | Cleaned Dundee sessions. QC summary says the clean dataset has 387,843 rows. Expected columns come from `clean_dundee.py`: session/station/chargepoint IDs, connector type, energy, arrival/departure, duration, postcode, date parts, hour, and 15-minute slot. |
| `data/interim/dundee_sessions_model_ready.parquet` | QC-filtered model-ready Dundee sessions. QC summary says it has 377,070 rows after removing 10,773 unusable rows. Adds connector power assumptions, implied power, approximate departure, chargepoint-station counts, and QC flags. |

### Processed Data

| File | Contents |
| --- | --- |
| `data/processed/.gitignore` | Ignores generated `background_load_15min.csv`. |
| `data/processed/.gitkeep` | Keeps the processed directory. |
| `data/processed/chargepoint_master.csv` | 90 chargepoint rows with station ID, connector mode, assumed port power, first/last seen year, and session totals. |
| `data/processed/station_master.csv` | 35 station rows with station metadata, chargepoint totals, connector mix, power proxy, years seen, sessions, energy, coordinates, and notes. |
| `data/processed/station_locations.csv` | 35 station location seed rows with lat/lon, source, confidence, and manual-review flag. |
| `data/processed/station_location_overrides.csv` | 35 station location override workflow rows with original/override coordinates, recommendations, reviewer, and review metadata. |
| `data/processed/station_locations_verified.csv` | 35 final station coordinate rows after override workflow, including verification status and confidence. |
| `data/processed/station_catalog.geojson` | GeoJSON feature collection for the 35 station catalog entries. |
| `data/processed/station_zone_map.csv` | 35 station-to-zone assignments across four simulator zones. |
| `data/processed/transformer_station_map.csv` | 35 station-to-transformer assignments with synthetic topology notes and assumed station capacity. |
| `data/processed/transformers.csv` | 8 synthetic transformer rows with zone, station counts, capacity assumptions, centroids, source, and notes. |
| `data/processed/zones.csv` | 4 simulator zone rows with descriptions, station/chargepoint counts, capacity totals, centroids, source, and notes. |
| `data/processed/request_replay_2023.csv` | 117,701 simulator replay requests for 2023 with arrival/deadline slots, station/zone/transformer mapping, energy/duration, preferences, charger type, and source metadata. |
| `data/processed/request_replay_2024.csv` | 90,320 simulator replay requests for 2024 with the same replay schema. |
| `data/processed/request_generator_params.json` | Priors and assumptions for synthetic request generation: arrival distributions, request counts, energy/duration/window/slack summaries, zone demand shares, preferences, dropped-session counts, and exogenous input metadata. |
| `data/processed/price_table_15min.csv` | 70,176 system-wide 15-minute tariff rows over 2023-2024 with weekday/weekend blocks and GBP/pence per kWh assumptions. |
| `data/processed/pv_profile_15min.csv` | 70,176 normalized 15-minute PV profile rows over 2023-2024 with capacity factor and kW per 1 MW installed PV. |
| `data/processed/station_capacity_assumptions.csv` | Intended to contain 50 lines of station capacity assumptions, but the file currently starts with binary-looking bytes rather than a CSV header. It appears corrupted or mislabeled. |

Note: `DundeeSimulationRepository` looks for `data/processed/background_load_15min.csv`,
but this repository does not currently contain that file. The repository code has
a deterministic fallback builder for background load.

## Notebooks

| File | Contents |
| --- | --- |
| `notebooks/01_data_overview.ipynb` | One-cell notebook headed `01 Data Overview`. |
| `notebooks/01_dundee_qc_and_eda.ipynb` | Four-cell notebook headed `Dundee QC and EDA`. |
| `notebooks/02_preprocessing_plan.ipynb` | One-cell notebook headed `02 Preprocessing Plan`. |
| `notebooks/03_environment_design.ipynb` | One-cell notebook headed `03 Environment Design`. |

## Outputs

### Figures

| File | Contents |
| --- | --- |
| `outputs/figures/.gitkeep` | Keeps the figures directory. |
| `outputs/figures/dundee_demand_growth_sessions_by_year.png` | Static chart of Dundee session-count growth by year. |
| `outputs/figures/dundee_energy_by_year_kwh.png` | Static chart of Dundee energy by year. |
| `outputs/figures/dundee_daily_energy_2024_bar.png` | Static bar chart of reconstructed model-ready daily energy for 2024. |
| `outputs/figures/dundee_daily_raw_energy_2024_bar.png` | Static bar chart of raw daily energy for 2024. |
| `outputs/figures/dundee_daily_energy_2024_comparison.png` | Static comparison chart of raw versus reconstructed/filtered daily energy. |
| `outputs/figures/dundee_hourly_load_profile_bar.png` | Static hourly load-profile chart. |
| `outputs/figures/dundee_station_map.png` | Static station map. |
| `outputs/figures/dundee_station_map_colored_by_cp_count.png` | Static station map colored by chargepoint count. |
| `outputs/figures/dundee_station_map_colored_by_sessions.png` | Static station map colored by session volume. |
| `outputs/figures/dundee_zone_transformer_map.png` | Static zone/transformer topology map. |

### Maps

| File | Contents |
| --- | --- |
| `outputs/maps/dundee_station_map_interactive.html` | Interactive station map. |
| `outputs/maps/dundee_station_map_interactive_by_cp_count.html` | Interactive station map styled by chargepoint count. |
| `outputs/maps/dundee_station_map_interactive_by_sessions.html` | Interactive station map styled by session volume. |
| `outputs/maps/dundee_zone_transformer_map.html` | Interactive zone/transformer topology map. |

### QC Reports

| File | Contents |
| --- | --- |
| `outputs/qc/dundee_quality_summary.md` | Human-readable Dundee QC summary: 387,843 clean rows, 377,070 model-ready rows, 10,773 removed, QC flags, top stations, and generated plots. |
| `outputs/qc/dundee_quality_summary.csv` | 39 structured QC summary rows. |
| `outputs/qc/dundee_request_replay_notes.md` | Methodology and assumptions for replay request construction. |
| `outputs/qc/dundee_request_replay_summary.md` | Human-readable replay summary with request counts, zone/station distribution, arrival histograms, and assumptions. |
| `outputs/qc/dundee_request_replay_summary.csv` | 102 structured replay summary rows. |
| `outputs/qc/dundee_visual_review_notes.md` | Notes on late-October raw versus reconstructed energy checks and map rendering. |
| `outputs/qc/dundee_zone_design_notes.md` | Explains synthetic simulator zones and transformer assumptions; explicitly says it is not verified utility topology. |
| `outputs/qc/station_location_review_summary.md` | Station coordinate review summary: 35 total stations, 28 accepted current, 0 manually overridden. |

### Runtime Outputs

| File | Contents |
| --- | --- |
| `outputs/runtime/event_log.jsonl` | Runtime event history as JSON lines. Starts with reset/runtime-started events from April 14, 2026 wall-clock timestamps and June 10, 2024 simulated timestamps. |
| `outputs/runtime/latest_external_requests.json` | Recent external request list; currently 5 items. |
| `outputs/runtime/recent_recommendations.json` | Recent recommendation responses; currently 6 items. |
| `outputs/runtime/runtime_status.json` | Runtime liveness/status fields such as loop state, mode, active policy, demand multiplier, replay day/year, latest request, and request/session counts. |
| `outputs/runtime/runtime_storage_config.json` | Points runtime storage at the configured SQLite DB path. |
| `outputs/runtime/sample_contract_manifest.json` | Manifest linking sample external request and recommendation response JSON files. |
| `outputs/runtime/sample_external_request.json` | Example live-style external charging request contract. |
| `outputs/runtime/sample_recommendation_response.json` | Example recommendation response contract. |
| `outputs/runtime/latest_metrics.json` | Intended latest metrics snapshot, but currently truncated before closing JSON. |
| `outputs/runtime/latest_state.json` | Intended latest full state snapshot, but currently truncated before closing JSON. |
| `outputs/runtime/sim_runtime.db` | Empty SQLite file. |
| `outputs/runtime/sim_runtime_local.db` | Large runtime SQLite file, but Python SQLite reports `database disk image is malformed`. |

### Empty Output Placeholders

| File | Contents |
| --- | --- |
| `outputs/logs/.gitkeep` | Keeps the logs output directory. |
| `outputs/metrics/.gitkeep` | Keeps the metrics output directory. |

## Important Observations

- The repository is in two phases at once: the mobile/API prototype is still
  partly mocked, while the Dundee simulator and runtime are much more developed.
- `apps/api` and `apps/mobile` are connected for recommendations through
  `POST /recommendations`, but the API station CRUD still uses simple mock data.
- `packages/ev_core` is intentionally independent of `apps/**`, and future
  integrations are expected to bind to its contracts.
- Several files appear corrupted or incomplete:
  - `packages/ev_core/README.md` contains binary-looking bytes.
  - `data/processed/station_capacity_assumptions.csv` contains binary-looking
    bytes despite its `.csv` extension.
  - `outputs/runtime/latest_metrics.json` and `outputs/runtime/latest_state.json`
    are truncated.
  - `outputs/runtime/sim_runtime_local.db` is reported malformed by SQLite.
- Some placeholders remain intentionally unimplemented: ACN cleaning, generic
  cleaning/feature-building helpers, several small builder scripts, and the
  reward model.
- `data/interim/*.csv` and `data/processed/background_load_15min.csv` are ignored,
  so some generated artifacts expected by scripts may exist locally in another
  run but are not present in this checkout.
