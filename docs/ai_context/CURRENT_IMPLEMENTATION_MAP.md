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
- `apps/api/app/services/recommendations_service.py`: maps normalized app/API `preference_mode` values (`closest`, `cheapest`, `fastest`) to the matching recommender policy name unless an explicit policy override is supplied, then delegates to `inject_live_request`.
- `apps/api/app/services/runtime_service.py`: cached `RuntimeManager`, runtime-start guard, runtime state/events/recommendation accessors. It now reads `DYNAMIC_PRICING_ENABLED`, `ROUTING_PROVIDER_NAME`, and `OSMNX_GRAPH_PATH` in addition to `RECOMMENDATION_POLICY_NAME` and optional `TOPOLOGY_SCENARIO_ID`.
- `apps/api/app/schemas/recommendations.py`: aliases API schemas to `ev_core.contracts.requests.ExternalChargingRequest` and `ev_core.contracts.responses.RecommendationResponse`.
- `apps/api/app/routers/system.py`: root, health, runtime status/state/events/recent recommendations endpoints.
- `apps/api/app/routers/stations.py` and `apps/api/app/services/stations_service.py`: mock CRUD station API backed by `apps/api/app/mock_data.py`.

## Mobile
- Mobile reservations and charging-session history are backend-backed through `/reservations`, `/sessions`, and internal `/charger-events` lifecycle endpoints.

- `apps/mobile/src/screens/ChargingRequestScreen.tsx`: collects `targetSoc`, `preferenceMode`, and `chargerType`.
- `apps/mobile/src/screens/LoadingRecommendationsScreen.tsx`: calls `api.getRecommendations(request)`, navigates to results on success.
- `apps/mobile/src/services/api.ts`: builds the backend JSON payload and calls `POST /recommendations`; resolves `API_BASE_URL` from `process.env.EXPO_PUBLIC_API_BASE_URL` or local platform defaults.
- `apps/mobile/env.d.ts`: declares optional `process.env.EXPO_PUBLIC_API_BASE_URL` for TypeScript.
- `apps/mobile/src/types.ts`: defines mobile request/response types matching the current API response shape.
- `apps/mobile/src/screens/ResultsScreen.tsx`: maps `top_recommendation` and `alternatives` into UI cards.

## Runtime Service

- `services/sim_runtime/runtime_manager.py`
  - `RuntimeConfig`: default replay year, policy, runtime mode, loop interval, demand multiplier, optional topology scenario, `dynamic_pricing_enabled`, `routing_provider_name`, and `osmnx_graph_path`.
  - `RuntimeManager.__init__`: loads Dundee data bundle, creates `PlaceholderForecastProvider`, `RuntimeStorage`, and `EventBus`.
  - `RuntimeManager.start`: creates `DundeeEnv`, starts it, persists state, optionally warm-starts, and passes through the dynamic-pricing toggle plus the configured routing provider.
  - `RuntimeManager.tick`: advances environment and persists state.
  - `RuntimeManager.inject_request`: loads env from persisted state, validates/builds `ExternalChargingRequest`, injects it, gets ranked recommendations, saves request/recommendation/state.
  - `RuntimeManager.recommend`: produces recommendations without queuing the request.
  - `RuntimeManager.get_latest_state`, `get_recent_events`, `get_recent_recommendations`, `get_runtime_status`: storage-backed read APIs.
  - Runtime status now surfaces active pricing/routing config including pricing model, dynamic-pricing toggle, routing provider name/availability, OSMnx graph path/existence, and last routing fallback reason.
- `services/sim_runtime/storage.py`
  - `RuntimeArtifacts`: paths under `outputs/runtime`.
  - `RuntimeStorage`: JSON plus SQLite persistence for state, metrics, events, external requests, and recommendations.
- `services/sim_runtime/event_bus.py`: event bus; currently used with a no-op wildcard subscriber in `RuntimeManager`.
- `services/sim_runtime/demo.py`, `scripts/digital_twin/run_demo_runtime.py`, `scripts/digital_twin/inject_live_request.py`: runtime demo/helper entry points. Legacy root-level wrappers remain temporarily.
- `scripts/verification/verify_station_access.py`: reports station access counts and normal-user eligibility for the real Dundee station table.
- `scripts/data/calibrate_transformer_capacities.py`: computes CP-inventory-based synthetic transformer capacity recommendations and can write calibrated realistic/stress topology scenario JSON files.
- `scripts/verification/verify_topology_scenario.py`: reports processed/default or optional scenario station-transformer counts, transformer capacities, connected CP kW, capacity warning flags, and validates every station maps to an existing transformer.
- `scripts/digital_twin/verify_runtime_smoke.py`: starts runtime, injects a live request, verifies persistence, and sweeps recommendation policies.
- `scripts/verification/verify_dynamic_pricing.py`: runtime-facing pricing smoke check that prints tariff/dynamic price metadata before and after added transformer stress.
- `scripts/verification/verify_dundee_tariff_pricing.py`: same-energy tariff sanity check for AC Standard, AC Fast, Rapid, and Ultra Rapid.
- `scripts/maps/evaluate_osmnx_routing_usefulness.py`: compares simple-distance and OSMnx routing across sampled Dundee request/station pairs and summarizes success/fallback rates.
- `scripts/digital_twin/verify_app_runtime_integration.py`: proves pricing/routing metadata and runtime status are connected to the app-facing recommendation path.
- `scripts/audit_repo_entrypoints.py`: dependency-light audit tooling that scans repo entrypoints, classifies scripts conservatively, searches references, and can render Markdown or JSON reports including `docs/ai_context/SCRIPT_AND_FILE_AUDIT.md`.
- `docs/ai_context/SCRIPT_AND_FILE_AUDIT.md`: generated audit report for grouped implementation scripts, legacy compatibility wrappers, and conservative cleanup rules.

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
  - `DundeeEnv`: request-driven simulator. It keeps `_build_candidate_contexts` as a compatibility method, delegating candidate construction to `ev_core.recommender.candidates.CandidateBuilder`. Recommendation distance now goes through an injectable `routing_provider`, which defaults to `SimpleDistanceRoutingProvider` and preserves the previous simple lat/lon and zone-fallback behavior. It also builds `Station.connectors` from `chargepoint_master.csv` where available, falls back to synthetic connectors otherwise, tracks connector assignment internally for active sessions, and now prices candidates from the selected connector class plus capped dynamic transformer/congestion overlay while preserving the public response shape. It can accept an optional `TopologyScenario`/`TopologyScenarioProvider`; without one, processed topology behavior is unchanged.
- `packages/ev_core/src/ev_core/routing/*`
  - `providers.py`: lightweight `RoutingProvider` protocol and `RouteEstimate`.
  - `simple_distance.py`: default `SimpleDistanceRoutingProvider` plus shared compatibility helper for the existing lat/lon approximation.
  - `osmnx_provider.py`: optional `OSMnxRoutingProvider` that loads a local GraphML road graph lazily, estimates shortest road distance by edge length, derives duration from graph travel time or speed fallback, and safely falls back to simple distance when graph/backend requirements are missing or routing fails unless `fail_closed=True`.
- `packages/ev_core/src/ev_core/env/entities.py`
  - `Station`, `Transformer`, `SimulationRequest`, `ActiveChargingSession`, `GridContext`, `StationRuntimeState`. `Station` includes optional/default access flags for public, fleet-only, membership-required, follow-up-needed, and excluded sites. `ChargingConnector` now carries optional connector type / CP identity. `ActiveChargingSession` can store internal connector assignment. `SimulationRequest` can carry optional `vehicle_profile_id`, `vehicle_max_ac_kw`, and `vehicle_max_dc_kw`.
- `packages/ev_core/src/ev_core/env/baselines.py`
  - Allocation policies: `RandomPolicy`, `GreedyFastestServicePolicy`, `OverloadAwarePolicy`, `CostAwarePolicy`.
- `packages/ev_core/src/ev_core/env/allocator.py`
  - `AllocationDecision`, `AllocationPolicy`.
- `packages/ev_core/src/ev_core/recommender/ranker.py`
  - `CandidateContext`, `RecommendationInput`, `CandidateRanker`, `WeightedHeuristicRanker`.
- `packages/ev_core/src/ev_core/recommender/policy_registry.py`
  - `PolicyRegistry` resolves deterministic recommendation policy names (`weighted_score`, `closest`, `cheapest`, `fastest`, `overload_aware`). Future offline-trained RL/MARL inference should register here as a policy and fall back to a deterministic policy if a checkpoint is unavailable.
- `packages/ev_core/src/ev_core/recommender/candidates.py`
  - `CandidateBuilder`: builds recommendation `CandidateContext` objects from runtime station state while receiving Dundee-specific distance, wait, price, headroom, and charger-compatibility callables from `DundeeEnv`. Distance still enters as a callback, so candidate construction is decoupled from the concrete routing implementation. It can also consume optional station-aware pricing/metadata hooks plus CP-aware compatible-port-count and effective-power callables. It filters station access eligibility before compatibility/window checks. Duration estimation uses vehicle-aware helpers while preserving old station-average behavior when CP-aware hooks are absent. Candidate pricing and metadata are now request-aware, using the same selected connector/power path as duration.
- `packages/ev_core/src/ev_core/pricing/dynamic_pricing.py`
  - `DynamicPricingInput`, `DynamicPricingResult`, and `calculate_dynamic_price(...)`: deterministic transformer-load and congestion overlay used for displayed recommendation cost estimation only, now capped between `0.90x` and `1.75x`.
- `packages/ev_core/src/ev_core/pricing/dundee_tariffs.py`
  - Simple Dundee simulation tariff classifier and base prices:
    - `ac_standard`: `£0.50/kWh`
    - `ac_fast`: `£0.57/kWh`
    - `rapid`: `£0.69/kWh`
    - `ultra_rapid`: `£0.75/kWh`
  - Candidate pricing uses selected connector type/power rather than a station-wide average.
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
- `packages/ev_core/src/ev_core/analysis/rl_demand_realism.py`
  - `build_demand_realism_summary(...)`, `build_utilization_bands(...)`, and `suggest_episode_request_ranges(...)`: repo-backed RL demand sizing helpers used to estimate request-count ranges and confirm that historical demand is lighter than normal utilization for the current 35-station / 90-chargepoint topology.
- `packages/ev_core/src/ev_core/rl/*`
  - `contracts.py`: `ScenarioSeedSplit`, `RLEpisodeScenario`, and `EvaluationMetrics` frozen dataclasses for fixed-seed RL preparation.
  - `scenarios.py`: `RLScenarioSampler` plus `generate_requests_for_scenario(...)`, keeping `simple_distance` as the default RL routing provider and leaving OSMnx optional.
  - `baselines.py`: `RandomValidPolicy`, which selects only from already-feasible recommendation options.
  - `evaluation.py`: `BaselinePolicyEvaluator`, a lightweight request-centric baseline harness for `weighted_score`, `closest`, `cheapest`, `fastest`, `overload_aware`, and `random_valid`.
  - `env.py`: `DundeeStationSelectionEnv`, a Gymnasium-compatible masked single-agent station-selection skeleton. It is currently decision-level: it reuses `DundeeEnv` candidate generation, exposes one request at a time, computes reward from the chosen candidate, and advances to the next request without full closed-loop queue/session mutation yet.
  - `observations.py`: `ObservationBuilder` and `ObservationSpec` for the first fixed-size flat observation vector. Global request/time features are followed by per-station distance/wait/duration/cost/headroom/queue/utilization/compatibility/mask features in deterministic station order.
  - `action_mask.py`: station-level boolean action mask builder driven by feasible Dundee candidate contexts.
  - `rewards.py`: `StationSelectionReward` and RL-side `RewardBreakdown` for the first stable served/invalid/missed plus cost-distance-wait-duration-headroom reward contract.
  - `forecast_features.py`: `ForecastFeatureSnapshot` placeholder contract for future observation features; no forecasting model is implemented yet.
  - `metrics.py`: helper functions for aggregating deterministic evaluation outputs.

Future learned-policy integration remains out of this implementation: first train single-agent MaskablePPO offline, save checkpoints outside git, load them through a checkpoint-backed policy class, register that policy in `PolicyRegistry`, and let `RecommendationService` select it through the same policy-name path. MARL should come later and should not replace API/mobile/dashboard response contracts.
- `scripts/generate_synthetic_live_requests.py`
  - CLI for writing synthetic-live request JSONL to `outputs/runtime/synthetic_live_requests.jsonl`.
- `scripts/verify_synthetic_live_requests.py`
  - CLI smoke check that generates synthetic-live requests and verifies runtime recommendations.
- `scripts/analyze_rl_demand_realism.py`
  - CLI summary for station/chargepoint counts, request-rate estimates, and target normal/busy/stress episode sizing.
- `scripts/verify_rl_scenario_sampler.py`
  - CLI smoke check for PR2 scenario sampling, request generation, and one lightweight deterministic baseline evaluation.
- `scripts/verify_rl_env_skeleton.py`
  - CLI smoke check for PR3 Gymnasium environment reset/step behavior, observation shape, valid-action count, first-step reward, and short valid-action rollout.
- `scripts/build_dundee_osmnx_graph.py`
  - Internet-requiring helper script that builds `data/processed/routing/dundee_drive.graphml` from `Dundee, Scotland, United Kingdom` with OSMnx `network_type="drive"`.
- `scripts/verify_osmnx_routing_provider.py`
  - Verifies the optional OSMnx provider against real Dundee station data when a local graph exists; otherwise prints a build-first message and exits cleanly.
- `scripts/export_osmnx_route_preview.py`
  - Exports a manual-inspection GeoJSON route preview to `outputs/runtime/osmnx_route_preview.geojson` when the local graph exists.

## Dashboard

- `dashboards/sim_dashboard/app.py`: Streamlit dashboard with runtime controls, map, live feed, recommendation panel, metrics charts, and visible runtime pricing/routing configuration fields. It imports `RuntimeManager` and `RuntimeStorage` directly.

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
- `tests/rl/test_demand_realism_analysis.py`: RL demand-realism summaries and episode-sizing helper coverage.
- `tests/rl/test_scenario_sampler.py`: fixed-seed split determinism, request-count bands, and scenario request metadata coverage.
- `tests/rl/test_rl_evaluation_contracts.py`: evaluation contract serialization, forecast placeholder defaults, and lightweight baseline evaluation smoke coverage.
- `tests/rl/test_random_valid_baseline.py`: `random_valid` feasible-option-only and deterministic selection coverage.
- `tests/rl/test_action_mask.py`: feasible-candidate to station-mask mapping coverage.
- `tests/rl/test_observation_builder.py`: deterministic vector size, seed repeatability, and finite-value coverage for the PR3 observation builder.
- `tests/rl/test_rewards.py`: served vs invalid reward ordering and penalty sensitivity coverage.
- `tests/rl/test_station_selection_env.py`: Gymnasium import/reset/step/mask/termination coverage for the PR3 environment skeleton.
- `tests/routing/test_simple_distance_provider.py`: default provider and legacy-distance behavior.
- `tests/routing/test_osmnx_provider.py`: missing-graph fallback, fail-closed behavior, import safety without OSMnx, fake-graph route calculation, duration fallback, and safe `DundeeEnv` provider injection.
- `tests/pricing/test_dundee_tariffs.py`: charger-class tariff classification and same-multiplier price ordering.
- `tests/sim_runtime/test_synthetic_live_runtime.py`: verifies a generated synthetic-live request can use the runtime recommendation path.
- `tests/recommender/*`, `tests/contracts/*`, `tests/vehicles/*`, `tests/api/*`, and `tests/sim_runtime/*`: focused coverage added across the recommendation refactor series.

## Config Boundaries (PR2)

- `packages/ev_core/src/ev_core/config/*`: additive configuration contracts for runtime, recommendation, routing, pricing, topology, training, deployment, and shared project paths.
- `ev_core.config` is import-safe and does not depend on FastAPI, Streamlit, dashboard modules, or runtime storage internals.
- API runtime config parsing in `apps/api/app/services/runtime_service.py` now uses `ev_core.config` env helpers while preserving existing defaults and behavior.

## Cleanup Status

- Script grouping is now applied under workflow folders in `scripts/`.
- Root-level script names are temporary backward-compatible wrappers for common/manual entrypoints.
- The audit currently keeps `outputs/test_data` intentionally in place.
- Any future script deletion still requires explicit user approval after audit evidence and passing tests.
