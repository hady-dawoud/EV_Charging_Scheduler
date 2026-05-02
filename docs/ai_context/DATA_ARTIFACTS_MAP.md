# Data Artifacts Map

Primary loader: `packages/ev_core/src/ev_core/data/repositories.py`.

`DundeeSimulationRepository.load_bundle()` loads a `DundeeDataBundle` with stations, transformers, zones, chargepoints, replay requests, request generator params, background load, prices, and PV profile.

## Station Catalog

- `data/processed/station_master.csv`
  - Fields observed: `station_id`, `station_name`, `postcode_mode`, `cp_count_total`, `connector_mix_total`, `station_max_power_kw_proxy`, `first_seen_year`, `last_seen_year`, `sessions_total`, `energy_total_kwh`, `latitude`, `longitude`, `location_source`, `notes`.
- `data/processed/chargepoint_master.csv`
  - Fields observed: `cp_id`, `station_id`, `connector_type_mode`, `assumed_port_kw`, `first_seen_year`, `last_seen_year`, `sessions_total`.
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

The topology notes state these are synthetic simulator feeder assignments, not verified utility topology.

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

## Price

- `data/processed/price_table_15min.csv`
  - Fields observed: `timestamp`, `date`, `year`, `month`, `weekday_name`, `is_weekend`, `hour`, `quarter_hour_slot`, `tariff_block`, `price_gbp_per_kwh`, `price_p_per_kwh`, `assumption_version`, `assumption_notes`.
  - Loaded by `DundeeSimulationRepository._load_price_table`.
  - Used through `PlaceholderForecastProvider.forecast_price`.

## PV

- `data/processed/pv_profile_15min.csv`
  - Fields observed: `timestamp`, `date`, `year`, `month`, `hour`, `quarter_hour_slot`, `pv_capacity_factor`, `pv_generation_kw_per_mw`, `assumption_version`, `assumption_notes`.
  - Loaded by `DundeeSimulationRepository._load_pv_profile`.
  - Used through `PlaceholderForecastProvider.forecast_pv_generation`.

## Background Load

- Expected path: `data/processed/background_load_15min.csv`.
- Current workspace status: file not found.
- `DundeeSimulationRepository._load_background_load(transformers)` catches decode/parser failure, but not `FileNotFoundError`. However, the current runtime has previously produced persisted state, so this may depend on local generated/ignored files or fallback behavior not fully verified in this inspection.
- Important follow-up: verify `RuntimeManager(repo_root).bundle.background_load` from a clean checkout.

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

