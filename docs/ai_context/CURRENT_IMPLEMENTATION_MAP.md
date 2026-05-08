# Current Implementation Map

Last verified against repo state: 2026-05-08.

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
- `apps/api/app/services/runtime_service.py`: cached `RuntimeManager`, runtime-start guard, runtime state/events/recommendation accessors. It now reads `DYNAMIC_PRICING_ENABLED` in addition to `RECOMMENDATION_POLICY_NAME` and optional `TOPOLOGY_SCENARIO_ID`.
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
  - `RuntimeConfig`: default replay year, policy, runtime mode, loop interval, demand multiplier, optional topology scenario, and `dynamic_pricing_enabled`.
  - `RuntimeManager.__init__`: loads Dundee data bundle, creates `PlaceholderForecastProvider`, `RuntimeStorage`, and `EventBus`.
  - `RuntimeManager.start`: creates `DundeeEnv`, starts it, persists state, optionally warm-starts, and passes through the dynamic-pricing toggle.
  - `RuntimeManager.tick`: advances environment and persists state.
  - `RuntimeManager.inject_request`: loads env from persisted state, validates/builds `ExternalChargingRequest`, injects it, gets ranked recommendations, saves request/recommendation/state.
  - `RuntimeManager.recommend`: produces recommendations without queuing the request.
  - `RuntimeManager.get_latest_state`, `get_recent_events`, `get_recent_recommendations`, `get_runtime_status`: storage-backed read APIs.
- `services/sim_runtime/storage.py`
  - `RuntimeArtifacts`: paths under `outputs/runtime`.
  - `RuntimeStorage`: JSON plus SQLite persistence for state, metrics, events, external requests, and recommendations.
- `services/sim_runtime/event_bus.py`: event bus; currently used with a no-op wildcard subscriber in `RuntimeManager`.
- `services/sim_runtime/demo.py`, `scripts/run_demo_runtime.py`, `scripts/inject_live_request.py`: runtime demo/helper entry points.
- `scripts/verify_station_access.py`: reports station access counts and normal-user eligibility for the real Dundee station table.
- `scripts/calibrate_transformer_capacities.py`: computes CP-inventory-based synthetic transformer capacity recommendations and can write calibrated realistic/stress topology scenario JSON files.
- `scripts/verify_topology_scenario.py`: reports processed/default or optional scenario station-transformer counts, transformer capacities, connected CP kW, capacity warning flags, and validates every station maps to an existing transformer.
- `scripts/verify_runtime_smoke.py`: starts runtime, injects a live request, verifies persistence, and sweeps recommendation policies.
- `scripts/verify_dynamic_pricing.py`: runtime-facing pricing smoke check that prints base/dynamic price metadata before and after added transformer stress.

## EV Core

- `packages/ev_core/src/ev_core/contracts/requests.py`
  - `ExternalChargingRequest`: current live request contract with domain validation for SOC, battery capacity, requested energy, energy/SOC consistency, timestamp ordering, global coordinate bounds, supported charger types, and optional vehicle max AC/DC power fields. Missing requested energy is inferred from SOC/battery when possible and otherwise defaults to `20.0` for compatibility.
  - `PreferenceMode`: `closest`, `cheapest`, `fastest`.
  - `SourceType`: `replay_background`, `synthetic_background`, `external_live`.
- `packages/ev_core/src/ev_core/contracts/responses.py`
  - `RecommendationOption`, `RecommendationResponse`.
  - `RequestSnapshot`, `StationStateSnapshot`, `TransformerStateSnapshot`, `MetricsSnapshot`, `StateSnapshot`.
- `packages/ev_core/src/ev_core/contracts/events.py`
  - `RuntimeEvent`.
- `packages/ev_core/src/ev_core/env/dundee_env.py`
  - `DundeeEnv`: request-driven simulator. It keeps `_build_candidate_contexts` as a compatibility method, delegating candidate construction to `ev_core.recommender.candidates.CandidateBuilder`. Recommendation distance now goes through an injectable `routing_provider`, which defaults to `SimpleDistanceRoutingProvider` and preserves the previous simple lat/lon and zone-fallback behavior. It also builds `Station.connectors` from `chargepoint_master.csv` where available, falls back to synthetic connectors otherwise, tracks connector assignment internally for active sessions, and can expose station-aware dynamic pricing metadata while preserving the public response shape. It can accept an optional `TopologyScenario`/`TopologyScenarioProvider`; without one, processed topology behavior is unchanged.
- `packages/ev_core/src/ev_core/routing/*`
  - `providers.py`: lightweight `RoutingProvider` protocol and `RouteEstimate`.
  - `simple_distance.py`: default `SimpleDistanceRoutingProvider` plus shared compatibility helper for the existing lat/lon approximation.
- `packages/ev_core/src/ev_core/env/entities.py`
  - `Station`, `Transformer`, `SimulationRequest`, `ActiveChargingSession`, `GridContext`, `StationRuntimeState`. `Station` includes optional/default access flags for public, fleet-only, membership-required, follow-up-needed, and excluded sites. `ChargingConnector` now carries optional connector type / CP identity. `ActiveChargingSession` can store internal connector assignment. `SimulationRequest` can carry optional `vehicle_profile_id`, `vehicle_max_ac_kw`, and `vehicle_max_dc_kw`.
- `packages/ev_core/src/ev_core/env/baselines.py`
  - Allocation policies: `RandomPolicy`, `GreedyFastestServicePolicy`, `OverloadAwarePolicy`, `CostAwarePolicy`.
- `packages/ev_core/src/ev_core/env/allocator.py`
  - `AllocationDecision`, `AllocationPolicy`.
- `packages/ev_core/src/ev_core/recommender/ranker.py`
  - `CandidateContext`, `RecommendationInput`, `CandidateRanker`, `WeightedHeuristicRanker`.
- `packages/ev_core/src/ev_core/recommender/candidates.py`
  - `CandidateBuilder`: builds recommendation `CandidateContext` objects from runtime station state while receiving Dundee-specific distance, wait, price, headroom, and charger-compatibility callables from `DundeeEnv`. Distance still enters as a callback, so candidate construction is decoupled from the concrete routing implementation. It can also consume optional station-aware pricing/metadata hooks plus CP-aware compatible-port-count and effective-power callables. It filters station access eligibility before compatibility/window checks. Duration estimation uses vehicle-aware helpers while preserving old station-average behavior when CP-aware hooks are absent.
- `packages/ev_core/src/ev_core/pricing/dynamic_pricing.py`
  - `DynamicPricingInput`, `DynamicPricingResult`, and `calculate_dynamic_price(...)`: deterministic transformer-load and congestion overlay used for displayed recommendation cost estimation only.
- `packages/ev_core/src/ev_core/recommender/eligibility.py`
  - `StationEligibilityFilter`: blocks excluded, non-public, fleet-only, and membership-required stations by default, with request-metadata overrides for non-public/fleet/membership sites. `needs_followup` is informational and does not block recommendations.
- `packages/ev_core/src/ev_core/recommender/service.py`
  - `RecommendationService`: calls ranker, assembles `RecommendationResponse`.
- `packages/ev_core/src/ev_core/vehicles/profiles.py`
  - `VehicleProfile` and in-code default vehicle profiles for small, mid-size, large, and van EVs.
- `packages/ev_core/src/ev_core/vehicles/duration.py`
  - Vehicle-aware station-level and connector-level effective-power helpers plus the shared 15-minute duration estimator used by candidate construction.
- `packages/ev_core/src/ev_core/data/repositories.py`
  - `DundeeDataPaths`, `DundeeDataBundle`, `DundeeSimulationRepository`. Station loading optionally merges `data/processed/station_access_overrides.csv` by `station_id`, normalizes access booleans, validates unknown override IDs, and defaults missing access flags to public/unrestricted. Missing background load CSV falls back to generated background load. The repository can load optional JSON topology scenarios from `data/processed/topology_scenarios`, but does not apply them by default.
- `packages/ev_core/src/ev_core/topology/scenarios.py`
  - `TransformerScenario`, `TopologyScenario`, `TopologyScenarioProvider`, and JSON scenario loading.
  - Scenario overlays can remap stations to transformers and apply static transformer capacity derating.
  - Current scope is lightweight synthetic topology configuration only: no routing, no dynamic reconfiguration, no MARL/RL.
- `packages/ev_core/src/ev_core/topology/capacity_calibration.py`
  - Lightweight capacity calibration helpers for synthetic transformer scenarios.
  - Uses connected CP kW from `chargepoint_master.csv`, max single CP kW, station count, simple diversity assumptions, and standard active-power capacity steps.
  - Produces calibrated realistic and stress recommendations plus warning flags for obviously low synthetic capacities.
- `packages/ev_core/src/ev_core/forecasting/provider.py`
  - `ForecastProvider`, `NullForecastProvider`, `PlaceholderForecastProvider`.
- `packages/ev_core/src/ev_core/generation/synthetic_live.py`
  - `SyntheticLiveRequestGenerator`: creates fresh mobile/API-style `ExternalChargingRequest` objects with `source_type="external_live"`, synthetic-live metadata, Dundee historical priors, station/zone anchor sampling, jittered origins, and default vehicle profile fields. It does not depend on `DundeeEnv` and does not replace replay or `synthetic_background`.
- `scripts/generate_synthetic_live_requests.py`
  - CLI for writing synthetic-live request JSONL to `outputs/runtime/synthetic_live_requests.jsonl`.
- `scripts/verify_synthetic_live_requests.py`
  - CLI smoke check that generates synthetic-live requests and verifies runtime recommendations.

## Dashboard

- `dashboards/sim_dashboard/app.py`: Streamlit dashboard with runtime controls, map, live feed, recommendation panel, and metrics charts. It imports `RuntimeManager` and `RuntimeStorage` directly.

## Tests

- `tests/data/test_station_access_overrides.py`: station access override merge, boolean parsing, unknown ID validation, and real override file public/default behavior.
- `tests/sim_runtime/test_runtime_smoke.py`: pandas-gated runtime start, live recommendation smoke, persistence, and policy sweep.
- `tests/recommender/test_cp_aware_availability.py`: CP-aware connector loading, compatibility, busy-port accounting, power selection, and connector assignment coverage.
- `tests/data/test_chargepoint_inventory.py`: bundle chargepoint inventory loading smoke test.
- `tests/data/test_topology_scenario_loading.py`: JSON topology scenario loading and bad-file validation.
- `tests/topology/test_topology_scenarios.py`: provider behavior, mapping validation, default preservation, and capacity derating.
- `tests/topology/test_capacity_calibration.py`: standard capacity rounding, realistic/stress sizing rules, warning flags, CP-load aggregation, fallback proxy behavior, and required-column validation.
- `tests/topology/test_calibrated_topology_scenarios.py`: calibrated scenario loading, station/transformer consistency, realistic capacity checks against CP inventory, and runtime startup with realistic/stress scenarios.
- `tests/sim_runtime/test_topology_scenario_runtime.py`: `DundeeEnv` and runtime-manager scenario integration while preserving default topology behavior.
- `tests/generation/test_synthetic_live_generator.py`: contract validity, determinism, SOC/energy consistency, vehicle fields, location/preference/charger validity, and batch generation coverage.
- `tests/sim_runtime/test_synthetic_live_runtime.py`: verifies a generated synthetic-live request can use the runtime recommendation path.
- `tests/recommender/*`, `tests/contracts/*`, `tests/vehicles/*`, `tests/api/*`, and `tests/sim_runtime/*`: focused coverage added across the recommendation refactor series.
