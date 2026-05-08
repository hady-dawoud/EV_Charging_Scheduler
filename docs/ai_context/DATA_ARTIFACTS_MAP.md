# Data Artifacts Map

Primary loader: `packages/ev_core/src/ev_core/data/repositories.py`.

`DundeeSimulationRepository.load_bundle()` loads a `DundeeDataBundle` with stations, transformers, zones, chargepoints, replay requests, request generator params, background load, prices, and PV profile.

## Station Catalog

- `data/processed/station_master.csv`
  - Fields observed: `station_id`, `station_name`, `postcode_mode`, `cp_count_total`, `connector_mix_total`, `station_max_power_kw_proxy`, `first_seen_year`, `last_seen_year`, `sessions_total`, `energy_total_kwh`, `latitude`, `longitude`, `location_source`, `notes`.
  - Optional access fields now supported by the loader if present: `is_public`, `is_fleet_only`, `requires_membership`, `needs_followup`, `exclude_from_recommendations`, `access_notes`.
  - If access fields are absent, stations default to public/unrestricted and remain eligible.
- `data/processed/station_access_overrides.csv`
  - Fields: `station_id`, `is_public`, `is_fleet_only`, `requires_membership`, `needs_followup`, `exclude_from_recommendations`, `access_notes`, `review_status`, `review_source`.
  - Merged by `DundeeSimulationRepository.load_station_table()` when present.
  - Project assumption: the Dundee dataset is treated as a public charging-station dataset. Stations stay public unless verified source data confirms restriction.
  - Current rows are review metadata only: `is_public=true`, `is_fleet_only=false`, `requires_membership=false`, and `exclude_from_recommendations=false`.
  - `needs_followup=true` marks data/location/access review needs, not automatic exclusion.
  - Runtime logic does not hardcode station IDs; any future restrictions must be data-driven and verified.
- `data/processed/chargepoint_master.csv`
  - Fields observed: `cp_id`, `station_id`, `connector_type_mode`, `assumed_port_kw`, `first_seen_year`, `last_seen_year`, `sessions_total`.
  - `DundeeEnv._build_station_index(...)` now uses these rows to build `Station.connectors` when present.
  - Current realism assumption: each CP row is treated as one usable connector/port; multi-head charger modelling is still future work.
- `data/processed/station_catalog.geojson`
  - GeoJSON FeatureCollection with station point geometry and properties such as `station_id`, `station_name`, `postcode_mode`, `cp_count_total`, `connector_mix_total`, `station_max_power_kw_proxy`.

## Station Locations

- `data/processed/station_locations.csv`
  - Fields observed: `station_id`, `station_name`, `postcode_mode`, `latitude`, `longitude`, `location_source`, `location_confidence`, `needs_manual_review`.
- `data/processed/station_location_overrides.csv`
  - Fields observed: original location fields, review recommendation/note, override fields, reviewer fields.
- `data/processed/station_locations_verified.csv`
  - Fields observed: original/override/final lat/lon, `verification_status`, `location_confidence_final`, `needs_followup_flag`, `verification_notes`.

`DundeeSimulationRepository.load_station_table()` uses `station_locations_verified.csv` and reads `final_latitude`/`final_longitude`, then exposes them as `latitude`/`longitude`.

Station access classification is now mechanically data-driven through `station_access_overrides.csv`. The current override file keeps all rows public and uses `needs_manual_review`/`needs_followup` for manual review tracking.

Chargepoint inventory is now part of live runtime realism, not just a descriptive artifact: compatibility, free-port counting, and best-available power can all be driven by `chargepoint_master.csv` through `DundeeEnv`.

## Zones

- `data/processed/zones.csv`
  - Fields observed: `zone_id`, `zone_name`, `zone_description`, `design_basis`, `station_count`, `cp_count_total_proxy`, `station_capacity_kw_total`, `centroid_latitude`, `centroid_longitude`, `topology_source`, `notes`.
- `data/processed/station_zone_map.csv`
  - Fields observed: `station_id`, `zone_id`, `zone_name`, `zone_description`, `zone_design_basis`, `station_name`.

Zones are synthetic simulator planning assumptions, not formal network boundaries.

## Transformers And Topology

- `data/processed/transformers.csv`
  - Fields observed: `transformer_id`, `transformer_name`, `transformer_map_label`, `zone_id`, `station_count`, `cp_count_total_proxy`, `attached_station_capacity_kw_sum`, `transformer_diversity_factor`, `transformer_capacity_kw_assumed`, `latitude`, `longitude`, `topology_source`, `notes`.
- `data/processed/transformer_station_map.csv`
  - Fields observed: `station_id`, `transformer_id`, `transformer_name`, `transformer_map_label`, `zone_id`, `topology_source`, `notes`, `station_name`, `station_capacity_kw_assumed`.
- `data/processed/topology_scenarios/dundee_synthetic_v1.json`
  - JSON scenario artifact mirroring the current synthetic processed transformer/station layout.
  - Loaded only when an explicit topology scenario is requested; the default runtime still uses `transformers.csv` and `transformer_station_map.csv` through the station table.
  - Supports static per-transformer `capacity_derating_factor`, with effective capacity equal to `capacity_kw * capacity_derating_factor`.
- `data/processed/topology_scenarios/dundee_synthetic_v1_realistic.json`
  - Calibrated synthetic scenario using the same station-to-transformer mapping as `dundee_synthetic_v1.json`.
  - Transformer `capacity_kw` values are active-power modelling approximations derived from `chargepoint_master.csv` connected CP kW, max single CP kW, simple diversity factors, and an 80% utilisation planning limit.
  - These values are not certified transformer kVA ratings and are not utility-verified.
- `data/processed/topology_scenarios/dundee_synthetic_v1_stress.json`
  - Calibrated constrained scenario for overload/headroom stress testing.
  - Keeps capacities defensible against CP inventory while intentionally lower than the realistic scenario.

The topology notes state these are synthetic simulator feeder assignments, not verified utility topology.
Topology scenarios are configuration overlays for simulator experiments, not utility-verified grid models.
Legacy 150 kW multi-station capacities should be interpreted as old/stress assumptions, not necessarily realistic physical transformer ratings.

## Station Capacity

- `data/processed/station_capacity_assumptions.csv`
  - The file exists, but direct text inspection produced binary/corrupt-looking output in this workspace.
  - `DundeeSimulationRepository._safe_load_station_capacity_assumptions()` catches decode/parser failures and falls back to `_derive_station_capacity_assumptions()`.
  - Not verified whether pandas can currently parse this file in the active environment.

## Request Replay

- `data/processed/request_replay_2023.csv`
- `data/processed/request_replay_2024.csv`

Fields observed in `request_replay_2024.csv`:

- `request_id`
- `source_session_id`
- `arrival_ts`
- `arrival_slot`
- `zone_id`
- `zone_name`
- `transformer_id`
- `transformer_name`
- `station_id`
- `requested_energy_kwh`
- `requested_duration_minutes`
- `latest_finish_ts`
- `latest_finish_slot`
- `user_preference_mode`
- `charger_type_preference`
- `request_year`
- `source_year`
- `station_name`
- `cp_id`
- `connector_type`
- `assumed_connector_limit_kw`
- `aligned_window_minutes`
- `technical_min_duration_minutes`
- `slack_minutes`
- `weekday_type`
- `arrival_weekday_name`
- `arrival_hour`
- `arrival_month`
- `cp_count_total`
- `connector_mix_total`
- `station_max_power_kw_proxy`
- `verification_status`
- `location_confidence_final`

`DundeeEnv._select_replay_table` supports replay years `2023` and `2024`.

## Synthetic Request Parameters

- `data/processed/request_generator_params.json`
  - Fields observed include `version`, `timebase_minutes`, `source_years`, `request_counts_by_year`, `arrival_distributions`, and requested energy/duration summaries.
  - Used by `DundeeEnv._activate_synthetic_requests` and related synthetic request helpers.
  - Also used by `SyntheticLiveRequestGenerator` to create fresh mobile/API-style `ExternalChargingRequest` objects for demos, smoke tests, evaluation, and future MARL scenario inputs.
  - Synthetic-live generation uses historical priors but does not copy historical `request_id`, `session_id`, or `source_session_id`.

## Generated Synthetic-Live Outputs

- `outputs/runtime/synthetic_live_requests.jsonl`
  - Written by `scripts/generate_synthetic_live_requests.py`.
  - Contains JSONL-serialized `ExternalChargingRequest` objects with `source_type="external_live"` and `metadata.generator_type="synthetic_live"`.
  - Generated requests use station/zone jittered origins and default vehicle profiles. OSMnx/OSRM road-node origins are not implemented yet.

## Routing

- Recommendation routing is now abstracted in code under `packages/ev_core/src/ev_core/routing`.
- Default runtime behavior still uses `SimpleDistanceRoutingProvider`, which computes a simple lat/lon approximation or zone fallback distance rather than a road-network route.
- `data/processed/routing/.gitkeep`
  - Keeps the generated-routing artifact directory present in git.
- `data/processed/routing/*.graphml`
  - Generated local OSMnx graph artifacts such as `dundee_drive.graphml`.
  - Ignored in git. Build with `scripts/build_dundee_osmnx_graph.py`; do not commit.
- `data/processed/routing/*.gpkg`
- `data/processed/routing/*.osm`
  - Reserved ignored routing artifacts for future local export/import workflows.
- `outputs/runtime/osmnx_route_preview.geojson`
  - Optional manual-inspection route preview written by `scripts/export_osmnx_route_preview.py`.
  - Generated artifact, not for commit.
- Fake-graph unit tests cover provider logic without requiring a real Dundee graph or internet.
- OSRM remains future work; there is no OSRM service artifact in the repo yet.

## Price

- `data/processed/price_table_15min.csv`
  - Fields observed: `timestamp`, `date`, `year`, `month`, `weekday_name`, `is_weekend`, `hour`, `quarter_hour_slot`, `tariff_block`, `price_gbp_per_kwh`, `price_p_per_kwh`, `assumption_version`, `assumption_notes`.
  - Loaded by `DundeeSimulationRepository._load_price_table`.
  - Used through `PlaceholderForecastProvider.forecast_price`.
  - Remains the base/system tariff input even when dynamic recommendation pricing is enabled.
  - Grid-aware recommendation pricing is an overlay on top of this base tariff; it does not replace the underlying price provider artifact.

## PV

- `data/processed/pv_profile_15min.csv`
  - Fields observed: `timestamp`, `date`, `year`, `month`, `hour`, `quarter_hour_slot`, `pv_capacity_factor`, `pv_generation_kw_per_mw`, `assumption_version`, `assumption_notes`.
  - Loaded by `DundeeSimulationRepository._load_pv_profile`.
  - Used through `PlaceholderForecastProvider.forecast_pv_generation`.

## Background Load

- Expected path: `data/processed/background_load_15min.csv`.
- Current workspace status: file not found.
- `DundeeSimulationRepository._load_background_load(transformers)` now falls back to synthetic background load generation when the file is missing or unparsable.
- Runtime smoke verification covers clean-start loading without this generated file.

## Raw And Interim Data

- Raw Dundee CSVs:
  - `data/raw/dundee/dundee_sessions_2021_h2.csv`
  - `data/raw/dundee/dundee_sessions_2022.csv`
  - `data/raw/dundee/dundee_sessions_2023.csv`
  - `data/raw/dundee/dundee_sessions_2024.csv`
  - `data/raw/dundee/dundee_sessions_2025_ytd.csv`
- Interim parquet:
  - `data/interim/dundee_sessions_clean.parquet`
  - `data/interim/dundee_sessions_model_ready.parquet`
- `DundeeDataPaths.model_ready_csv` points to `data/interim/dundee_sessions_model_ready.csv`, but only a parquet file was observed. This matters only if replay CSV parsing falls back to `_build_replay_from_model_ready`.

## Generated Outputs

- `outputs/qc`: QC reports and summaries.
- `outputs/figures`: generated PNG charts and maps.
- `outputs/maps`: generated interactive HTML maps.
- `outputs/runtime`: runtime JSON, JSONL, SQLite, and sample request/response contracts.

