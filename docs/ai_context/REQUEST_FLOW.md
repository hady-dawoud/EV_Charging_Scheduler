# Request Flow

Last verified against repo state: 2026-05-08.

This is the verified live recommendation path from the mobile app to the runtime-backed response.

Synthetic-live generation now exists for demos/evaluation: `ev_core.generation.synthetic_live.SyntheticLiveRequestGenerator`
creates valid `ExternalChargingRequest` objects with `source_type="external_live"` and `metadata.generator_type="synthetic_live"`.
These generated requests are not replayed historical sessions and use the same runtime recommendation path as mobile/API requests.

## Mobile Request Creation

1. `apps/mobile/src/screens/ChargingRequestScreen.tsx`
   - User selects:
     - `targetSoc`
     - `preferenceMode`: `cheapest`, `fastest`, or `closest`
     - `chargerType`: `any`, `ac`, or `dc`
   - `handleFindRecommendations` navigates to `LoadingRecommendations` with a `MobileRecommendationRequest`.

2. `apps/mobile/src/screens/LoadingRecommendationsScreen.tsx`
   - Reads `route.params.request`.
   - Calls `api.getRecommendations(request)`.
   - On success, navigates to `Results` with the returned API result.

3. `apps/mobile/src/services/api.ts`
   - Resolves `API_BASE_URL` as `process.env.EXPO_PUBLIC_API_BASE_URL || LOCAL_API_BASE_URL`.
   - `LOCAL_API_BASE_URL` is `http://10.0.2.2:8000` on Android and `http://127.0.0.1:8000` otherwise.
   - `api.getRecommendations` builds payload:
     - `client_request_id`
     - `request_timestamp`
     - `current_latitude`
     - `current_longitude`
     - `target_soc`
     - `current_soc`
     - `battery_kwh`
     - `requested_energy_kwh`
     - `preference_mode`
     - `charger_type`
     - `latest_finish_ts`
     - `source_type`
     - `request_id`
     - `zone_id`
     - `metadata`
   - The backend request contract also accepts optional vehicle fields (`vehicle_profile_id`, `vehicle_max_ac_kw`, `vehicle_max_dc_kw`), but the current mobile payload does not require or send them.
   - Calls `fetch(`${API_BASE_URL}/recommendations`, { method: 'POST', ... })`.

## FastAPI Endpoint

4. `apps/api/app/main.py`
   - Reads `CORS_ORIGINS` from the environment, split by comma.
   - Default CORS origins are `http://localhost:8081`, `http://127.0.0.1:8081`, and `http://localhost:3000`.
   - Includes `recommendations_router`.

5. `apps/api/app/routers/recommendations.py`
   - `get_recommendations(request: RecommendationRequest) -> RecommendationsResponse`
   - `RecommendationRequest` is an alias to `ExternalChargingRequest`.
   - Calls `generate_recommendations(request)`.
   - Converts `RuntimeNotStartedError` into HTTP 409.

6. `apps/api/app/schemas/recommendations.py`
   - `RecommendationRequest = ExternalChargingRequest`
   - `RecommendationsResponse = RecommendationResponse`

7. `packages/ev_core/src/ev_core/contracts/requests.py`
   - `ExternalChargingRequest` validates:
     - `extra="forbid"`
     - `request_timestamp` and `latest_finish_ts` normalized to naive UTC if timezone-aware.
     - `current_soc` and `target_soc`, when provided, are within `0..100`, and `target_soc > current_soc` when both are present.
     - `battery_kwh`, when provided, is positive and capped at a generous `250.0` kWh upper bound.
     - Optional `vehicle_profile_id`, `vehicle_max_ac_kw`, and `vehicle_max_dc_kw` are accepted without requiring mobile changes.
     - Optional vehicle max power values must be positive; current generous caps are `vehicle_max_ac_kw <= 50` and `vehicle_max_dc_kw <= 500`.
     - `requested_energy_kwh`, when provided or inferred, is positive and cannot exceed `battery_kwh` when battery capacity is known.
     - `requested_energy_kwh` inferred from `target_soc`, `current_soc`, `battery_kwh` if missing.
     - If still missing because SOC/battery data is unavailable, defaults to `20.0` for compatibility with existing clients.
     - Explicit `requested_energy_kwh` is compared against SOC-derived energy when SOC and battery are present; small absolute (`<=0.5` kWh) or relative (`<=5%`) differences are accepted, large mismatches fail validation.
     - `latest_finish_ts` must be after `request_timestamp`.
     - `current_latitude` and `current_longitude`, when provided, must be within global coordinate bounds.
     - `charger_type` is validated case-insensitively for currently supported mobile/API values: `Any`, `AC`, `DC`, `Rapid`, `UltraRapid`, and `ultra_rapid`.
   - Remaining validation gaps: Dundee bounding-box warnings, max request window policy, and future vehicle-profile-specific limits.

## Synthetic-Live Request Generation

- `packages/ev_core/src/ev_core/generation/synthetic_live.py`
  - `SyntheticLiveRequestGenerator` generates fresh app-like `ExternalChargingRequest` objects.
  - It uses `request_generator_params.json` priors for zone demand, preference shares, energy summaries, duration summaries, slack summaries, and timestamp weighting.
  - It samples local default vehicle profiles and populates `vehicle_profile_id`, `battery_kwh`, `vehicle_max_ac_kw`, and `vehicle_max_dc_kw`.
  - It keeps SOC and requested energy consistent so PR5 validation passes.
  - It chooses an anchor station/zone and jitters the current location around the anchor station. This is still station/zone-origin sampling, not road-node routing.
  - It sets `source_type="external_live"` so generated requests exercise the same API/runtime path as mobile requests.
  - It marks generated requests through metadata: `generator_type="synthetic_live"`, `generator_version="synthetic_live_v1"`, `anchor_station_id`, `anchor_zone_id`, and `synthetic_seed`.
- `scripts/generate_synthetic_live_requests.py` writes generated requests to `outputs/runtime/synthetic_live_requests.jsonl`.
- `scripts/verify_synthetic_live_requests.py` generates requests and verifies that `RuntimeManager.recommend(...)` returns a top recommendation.
- This is separate from `DundeeEnv._build_synthetic_request`, which still creates internal `synthetic_background` simulation requests.

## API Runtime Service

8. `apps/api/app/services/recommendations_service.py`
   - `generate_recommendations(request)` returns `inject_live_request(request)`.

9. `apps/api/app/services/runtime_service.py`
   - `get_runtime_manager()` returns cached `RuntimeManager(repo_root=REPO_ROOT)`.
   - `ensure_runtime_started()` checks `get_runtime_manager().get_latest_state()`.
   - `inject_live_request(request)` calls `ensure_runtime_started()` then `RuntimeManager.inject_request(request)`.

## Runtime Manager

10. `services/sim_runtime/runtime_manager.py`
    - `RuntimeManager.inject_request(payload)`:
      - `_load_env()` loads latest `StateSnapshot` from storage or creates a new `DundeeEnv`.
      - Converts dict payloads using `ExternalChargingRequest.model_validate`.
      - Calls `env.inject_external_request(request)`.
      - Calls `env.get_ranked_recommendations(sim_request)`.
      - Persists external request with `RuntimeStorage.save_external_request`.
      - Persists recommendation with `RuntimeStorage.save_recommendation`.
      - Persists state/metrics/events with `_persist_env(env, include_events=True)`.
      - Returns `RecommendationResponse`.

## Environment Injection

11. `packages/ev_core/src/ev_core/env/dundee_env.py`
    - `DundeeEnv.inject_external_request(request)`:
      - Calls `_build_simulation_request_from_external`.
      - Stores the `SimulationRequest` in `self.requests`.
      - Increments `requests_seen_total`.
      - Sets `latest_external_request_id`.
      - Records `external_request_injected` event.
    - `_build_simulation_request_from_external(request)`:
      - Uses provided `request_id` or generates `external_<uuid>`.
      - Floors `request_timestamp` to the 15-minute time base.
      - Derives `zone_id` from request zone or nearest station location.
      - Normalizes charger type.
      - Sets `requested_energy_kwh`.
      - Passes through optional vehicle fields `vehicle_profile_id`, `vehicle_max_ac_kw`, and `vehicle_max_dc_kw`.
      - Computes `requested_duration_minutes` from request window.
      - Returns `SimulationRequest`.

## Response Consumption

12. `apps/mobile/src/screens/ResultsScreen.tsx`
    - Reads `bundle.top_recommendation` and `bundle.alternatives`.
    - `mapOptionToUiStation` maps fields from `RecommendationOption` into UI station cards.
    - Uses `metadata.connector_mix_total` to infer charger display label.
