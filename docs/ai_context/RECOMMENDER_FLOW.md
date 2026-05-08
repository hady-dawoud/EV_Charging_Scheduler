# Recommender Flow

Last verified against repo state: 2026-05-08.

## Classification

The current recommendation output is deterministic weighted heuristic ranking. It is not MARL, not RL checkpoint inference, and not random. It is also not merely mock data for `/recommendations`; it ranks live candidate contexts generated from the Dundee runtime state.

Runtime allocation baselines can include stable pseudo-random choice during simulation, but that is separate from the recommender ranker used to score candidate stations.

## Candidate Construction

Candidate construction is owned by `packages/ev_core/src/ev_core/recommender/candidates.py`.

- `DundeeEnv.get_ranked_recommendations(request)` calls `_build_candidate_contexts(simulation_request)`.
- `DundeeEnv._build_candidate_contexts(request, only_station_id=None)` remains as a compatibility method and delegates to `CandidateBuilder`.
- `CandidateBuilder.build(...)` receives station/runtime state plus callables for distance, wait, price, transformer headroom, charger compatibility, optional CP-aware effective power, optional compatible-available-port counts, and optional station-aware pricing/metadata hooks.
- `CandidateBuilder.build(...)` applies `StationEligibilityFilter` before charger compatibility, duration, distance, or scoring work.
- `CandidateBuilder.build(...)` loops over the provided stations, currently `self.station_index.values()` from `DundeeEnv`.
- `DundeeEnv.station_index` may be built from the processed topology or from an optional `TopologyScenarioProvider` overlay. The default runtime still uses processed topology unless a scenario is explicitly configured.
- A station becomes a candidate only if:
  - station eligibility passes public/restricted access checks.
  - charger compatibility passes through `_is_charger_compatible` or CP-aware compatible-available-port checks when `DundeeEnv` provides them.
  - `estimated_duration + estimated_wait <= remaining_window_minutes`.
- Each candidate is a `CandidateContext` from `packages/ev_core/src/ev_core/recommender/ranker.py`.

Candidate fields:

- `station_id`
- `station_name`
- `zone_id`
- `transformer_id`
- `distance_km`
- `estimated_wait_minutes`
- `estimated_duration_minutes`
- `estimated_cost_gbp`
- `transformer_headroom_kw`
- `current_queue`
- `utilization`
- `charger_compatible`
- `metadata={"connector_mix_total": station.connector_mix_total, "price_per_kwh": ...}`
- optional pricing transparency fields such as `base_price_per_kwh`, transformer/congestion multipliers, load/headroom ratios, and pricing reason.

Supporting methods still supplied by `DundeeEnv`:

- `_distance_to_station_km`: uses location if available, otherwise zone fallback.
- `_distance_simple`: simple lat/lon approximation using `lat_scale = 111.0`, `lon_scale = 111.0 * 0.56`.
- `_estimate_station_wait_minutes`: zero if free ports and no queue, otherwise earliest active-session release plus 15 minutes per queued request.
- `_current_price_per_kwh`: uses `ForecastProvider.forecast_price` and remains the base/system tariff signal.
- `_current_station_price_per_kwh`: optional station-aware overlay that adjusts displayed recommendation price by transformer stress and station congestion.
- `_current_transformer_headroom`: transformer capacity minus net background load minus active EV load.
- `_is_charger_compatible`: checks requested AC/Rapid/Ultra Rapid/Any against `connector_mix_total`.

## Dynamic Pricing Overlay

- Grid-aware dynamic pricing now lives in `packages/ev_core/src/ev_core/pricing/dynamic_pricing.py`.
- This pricing is a simulation/display overlay only. It is not a real billing tariff, settlement price, or customer payment calculation.
- Base tariff still comes from `ForecastProvider.forecast_price` through `_current_price_per_kwh()`.
- `DundeeEnv._current_station_pricing_result(station_id)` combines:
  - base price
  - transformer capacity/net load/headroom
  - station queue length
  - station utilization
- High transformer load raises displayed `price_per_kwh`; high headroom can reduce it; queue/utilization add congestion uplift.
- `estimated_cost_gbp` now reflects this dynamic station-aware recommendation price when `dynamic_pricing_enabled=True`.
- Public response shape is unchanged. Pricing transparency is carried only through `RecommendationOption.metadata`.
- The `cheapest` policy naturally reacts to the overlay because it already ranks by `estimated_cost_gbp`.

## Topology Scenarios

- `packages/ev_core/src/ev_core/topology/scenarios.py` defines optional synthetic topology scenarios.
- `DundeeSimulationRepository.load_topology_scenario(...)` can load JSON scenarios from `data/processed/topology_scenarios`.
- `DundeeEnv` accepts an optional `TopologyScenario` or `TopologyScenarioProvider` and applies station-to-transformer overrides before building `Station` objects.
- Scenario transformer definitions replace the transformer table for that runtime and support static `capacity_derating_factor`.
- Effective capacity is `capacity_kw * capacity_derating_factor`, so scenarios can represent normal, constrained, or stress-test headroom assumptions.
- `capacity_kw` is an active-power simulator approximation. It is not a certified transformer kVA rating.
- `dundee_synthetic_v1_realistic.json` calibrates capacity assumptions from CP inventory using simple diversity/utilisation assumptions.
- `dundee_synthetic_v1_stress.json` keeps the same topology but uses constrained capacities for overload/headroom stress tests.
- The original `dundee_synthetic_v1.json` remains a legacy/mirrored processed scenario; its 150 kW multi-station feeders should not be treated as physically verified transformer ratings.
- This is still synthetic simulator topology, not verified utility topology.
- Time-varying topology, time-varying transformer capacity, routing, and MARL training/evaluation across realistic and stress scenarios remain future work.

## CP-Aware Availability

- `DundeeEnv._build_station_index(...)` now prefers `bundle.chargepoints` rows when building `Station.connectors`.
- Each `chargepoint_master.csv` row is treated as one lightweight usable connector/port for now.
- `ChargingConnector` now carries `connector_id`, `max_power_kw`, `connector_type`, and optional `cp_id`.
- If a station has no usable CP rows, `DundeeEnv` falls back to synthetic connectors derived from station capacity and `cp_count_total`.
- `DundeeEnv` now exposes CP-aware helpers for:
  - requested-type vs connector-type compatibility
  - available compatible connector counts
  - best available compatible connector power
  - selecting a connector when a session starts
- `CandidateBuilder` can now use CP-aware compatible-available-port counts and best-available power, so a station with no currently free compatible connector is skipped for that request.
- Queueing is still station-level. This is not a full per-head/per-plug simulator.
- `ActiveChargingSession` can track `connector_id` and `connector_type` internally when a session starts, but public response and snapshot models remain unchanged.

## Station Eligibility

Station access filtering lives in `packages/ev_core/src/ev_core/recommender/eligibility.py`.

- Project assumption: loaded Dundee station rows are public charging stations unless verified source data says otherwise.
- `StationEligibilityFilter` blocks stations marked `exclude_from_recommendations`, non-public stations, fleet-only stations, or membership-required stations for normal requests.
- `needs_followup=True` is informational/manual-review metadata and does not block recommendations.
- Request metadata can explicitly allow non-public, fleet-only, or membership sites with `allow_non_public_stations`, `allow_fleet_only`, or `allow_membership_sites`.
- `exclude_from_recommendations=True` remains blocked even when override metadata is present.
- `DundeeEnv._build_station_index` reads optional station access columns when present and defaults missing columns to public/unrestricted.
- `DundeeSimulationRepository.load_station_table()` merges `data/processed/station_access_overrides.csv` when present, so station access is data-driven before `DundeeEnv` builds `Station` objects.
- Runtime recommendation code does not hardcode station IDs. Current override data keeps all rows public and uses `needs_followup`/review notes for manual verification.

## Verification

- `scripts/verify_station_access.py` loads the real station table and reports total/public/fleet/membership/follow-up/excluded/eligible counts plus blocked reasons.
- `scripts/verify_runtime_smoke.py` starts the runtime, injects a mobile-style live request, verifies recommendation persistence, and sweeps `weighted_score`, `closest`, `cheapest`, `fastest`, and `overload_aware`.
- `scripts/verify_dynamic_pricing.py` starts the runtime, prints recommendation pricing metadata, adds artificial transformer stress, and re-checks displayed recommendation prices under the `cheapest` policy.
- `tests/sim_runtime/test_runtime_smoke.py` covers the same runtime start/recommendation and policy sweep paths when real pandas/numpy are installed.

## Vehicle-Aware Duration

Vehicle helpers live in `packages/ev_core/src/ev_core/vehicles`.

- `vehicles.profiles` defines a small in-code default catalog: `small_ev`, `mid_ev`, `large_ev`, and `van_ev`.
- `vehicles.duration.estimate_effective_power_kw` preserves the old station-average-power behavior when no CP-aware power callable is supplied.
- `vehicles.duration.estimate_connector_effective_power_kw` caps connector power by optional vehicle AC/DC limits.
- When `DundeeEnv` provides CP-aware power, `CandidateBuilder` uses the best available compatible connector power for duration estimation.
- Duration still uses the existing linear energy/power estimate, nearest 15-minute rounding, and minimum 15-minute duration.
- Charging curves, tapering, and CSV-backed vehicle catalogs remain future work.

## Synthetic-Live Inputs

Synthetic-live generation is implemented in `packages/ev_core/src/ev_core/generation/synthetic_live.py`.

- It creates new `ExternalChargingRequest` objects, not old session replays.
- It uses `source_type="external_live"` and metadata to identify generated requests.
- It uses Dundee priors from `request_generator_params.json`, station/zone distributions, and default vehicle profiles.
- Generated requests can be passed to `RuntimeManager.recommend(...)` or `RuntimeManager.inject_request(...)`.
- The existing `replay_background` and `synthetic_background` paths in `DundeeEnv` remain separate.

## Scoring

Scoring is in `packages/ev_core/src/ev_core/recommender/ranker.py`.

`WeightedHeuristicRanker.rank(payload)`:

1. Selects weights from `WEIGHTS` by `payload.preference_mode`, defaulting to `fastest`.
2. Calls `_score_candidate(candidate, weights)` for each candidate.
3. Calls `_reason_tags(candidate)`.
4. Creates `RecommendationOption`.
5. Sorts options by:
   - descending score
   - ascending estimated wait
   - ascending distance
   - ascending estimated cost

Scoring formula:

```text
compatibility = 1.0 if candidate.charger_compatible else 0.0
normalized_headroom = clamp(candidate.transformer_headroom_kw / 500.0, 0.0, 1.0)
wait_component = 1.0 / (1.0 + candidate.estimated_wait_minutes / 15.0)
duration_component = 1.0 / (1.0 + candidate.estimated_duration_minutes / 15.0)
distance_component = 1.0 / (1.0 + candidate.distance_km)
price_component = 1.0 / (1.0 + candidate.estimated_cost_gbp)

score =
  weights["distance"] * distance_component
  + weights["wait"] * wait_component
  + weights["headroom"] * normalized_headroom
  + weights["price"] * price_component
  + weights["duration"] * duration_component
  + weights["compatibility"] * compatibility
```

## Preference Weights

`closest`:

- `distance`: `0.45`
- `wait`: `0.20`
- `headroom`: `0.15`
- `price`: `0.10`
- `duration`: `0.05`
- `compatibility`: `0.05`

`cheapest`:

- `price`: `0.40`
- `distance`: `0.15`
- `wait`: `0.15`
- `headroom`: `0.15`
- `duration`: `0.10`
- `compatibility`: `0.05`

`fastest`:

- `wait`: `0.35`
- `duration`: `0.25`
- `headroom`: `0.20`
- `distance`: `0.10`
- `price`: `0.05`
- `compatibility`: `0.05`

## Reason Tags

Reason tags are generated in `WeightedHeuristicRanker._reason_tags(candidate)`:

- `nearby` if `distance_km <= 1.5`
- `low_wait` if `estimated_wait_minutes <= 15`
- `high_headroom` if `transformer_headroom_kw >= 100`
- `low_cost` if `estimated_cost_gbp <= 6.0`
- `charger_match` if `charger_compatible`
- Returns at most the first 4 tags.

## Response Assembly

Response assembly is in `packages/ev_core/src/ev_core/recommender/service.py`.

- `RecommendationService.__init__` defaults to `WeightedHeuristicRanker`.
- `RecommendationService.recommend(...)`:
  - calls `self.ranker.rank(RecommendationInput(...))`
  - sets `top_recommendation = ranked[0] if ranked else None`
  - sets `alternatives = ranked[1:4]`
  - builds `congestion_note` with `_build_congestion_note`
  - builds `debug_reasoning_summary` with `_build_debug_summary`
  - returns `RecommendationResponse`

Congestion notes:

- no ranked options: `No feasible station matched the request window and charger constraints.`
- top wait over 30 minutes: notable waiting time note.
- top transformer headroom below 50 kW: limited headroom note.

