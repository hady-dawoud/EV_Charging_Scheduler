# Recommender Flow

## Classification

The current recommendation output is deterministic weighted heuristic ranking. It is not MARL, not RL checkpoint inference, and not random. It is also not merely mock data for `/recommendations`; it ranks live candidate contexts generated from the Dundee runtime state.

Runtime allocation baselines can include stable pseudo-random choice during simulation, but that is separate from the recommender ranker used to score candidate stations.

## Candidate Construction

Candidate construction is in `packages/ev_core/src/ev_core/env/dundee_env.py`.

- `DundeeEnv.get_ranked_recommendations(request)` calls `_build_candidate_contexts(simulation_request)`.
- `_build_candidate_contexts(request, only_station_id=None)` loops over `self.station_index.values()`.
- A station becomes a candidate only if:
  - charger compatibility passes through `_is_charger_compatible`.
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
- `metadata={"connector_mix_total": station.connector_mix_total}`

Supporting methods in `DundeeEnv`:

- `_distance_to_station_km`: uses location if available, otherwise zone fallback.
- `_distance_simple`: simple lat/lon approximation using `lat_scale = 111.0`, `lon_scale = 111.0 * 0.56`.
- `_estimate_station_wait_minutes`: zero if free ports and no queue, otherwise earliest active-session release plus 15 minutes per queued request.
- `_current_price_per_kwh`: uses `ForecastProvider.forecast_price`.
- `_current_transformer_headroom`: transformer capacity minus net background load minus active EV load.
- `_is_charger_compatible`: checks requested AC/Rapid/Ultra Rapid/Any against `connector_mix_total`.

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

