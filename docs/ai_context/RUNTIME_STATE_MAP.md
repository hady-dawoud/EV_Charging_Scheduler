# Runtime State Map

## Storage Location

Runtime persistence is managed by `services/sim_runtime/storage.py`.

`RuntimeArtifacts.from_repo_root(repo_root)` stores files under `outputs/runtime`:

- `sim_runtime.db`
- `latest_state.json`
- `latest_metrics.json`
- `recent_recommendations.json`
- `latest_external_requests.json`
- `event_log.jsonl`
- `runtime_status.json`
- `runtime_storage_config.json`

The current workspace also contains `outputs/runtime/sim_runtime_local.db`; `RuntimeStorage._ensure_schema` can fall back to `sim_runtime_local.db` or `sim_runtime_store.db`.

SQLite tables created by `RuntimeStorage._initialize_schema`:

- `state_snapshots`
- `runtime_events`
- `metrics_snapshots`
- `recommendations`
- `external_requests`

## Runtime Manager

`services/sim_runtime/runtime_manager.py` owns runtime lifecycle:

- `RuntimeManager.start`: creates fresh `DundeeEnv`.
- `RuntimeManager.tick`: advances 15-minute steps.
- `RuntimeManager.start_loop` and `stop_loop`: background ticking loop.
- `RuntimeManager.inject_request`: injects external request and persists recommendation/state.
- `RuntimeManager.recommend`: recommends without queuing the request.
- `_persist_env`: saves `StateSnapshot`, `MetricsSnapshot`, runtime status, and events.

## Environment State

`packages/ev_core/src/ev_core/env/dundee_env.py` stores mutable environment state in memory, reconstructed from `StateSnapshot` as needed.

Important fields:

- `station_index`: static `Station` objects keyed by station id.
- `transformer_index`: static `Transformer` objects keyed by transformer id.
- `stations_runtime`: `StationRuntimeState` per station, with active and queued request ids.
- `requests`: `SimulationRequest` objects keyed by request id.
- `active_sessions`: `ActiveChargingSession` objects keyed by request id.
- `recent_events`: in-memory `RuntimeEvent` list since the current env construction/restore.
- `recently_completed_request_ids`
- `recently_missed_request_ids`
- `completed_requests_total`
- `missed_requests_total`
- `requests_seen_total`
- `overload_event_count`
- `latest_external_request_id`

## Entities

Defined in `packages/ev_core/src/ev_core/env/entities.py`:

- `Station`: static station definition with station id/name, zone, transformer, coordinates, connector mix, capacity, and connector list.
- `Transformer`: synthetic transformer definition with capacity and attached station ids.
- `SimulationRequest`: internal request state, including source type, timing, energy, preference, charger type, assigned station/transformer, status, queue/session timestamps, and metadata.
- `ActiveChargingSession`: active charging session occupying a station port.
- `GridContext`: background load, tariff, and PV signal for an interval.
- `StationRuntimeState`: active and queued request ids for a station.

## Snapshots

Defined in `packages/ev_core/src/ev_core/contracts/responses.py`:

- `StateSnapshot`: top-level persisted runtime state.
- `RequestSnapshot`: active/queued/session request state.
- `StationStateSnapshot`: station operational state for dashboard/API.
- `TransformerStateSnapshot`: transformer load/headroom state.
- `MetricsSnapshot`: compact metrics history.

`DundeeEnv.get_state_snapshot()` builds:

- `active_requests` from requests with status `pending`.
- `queued_requests` from requests with status `queued`.
- `active_sessions` from requests with status `charging`.
- `stations` via `_station_snapshot`.
- `transformers` via `_transformer_snapshot`.
- `metrics` via `_build_metrics_snapshot`.

## External Live Injection

`RuntimeManager.inject_request(payload)`:

1. Loads current env from latest persisted `StateSnapshot`.
2. Validates payload as `ExternalChargingRequest` if needed.
3. Calls `DundeeEnv.inject_external_request`.
4. Calls `DundeeEnv.get_ranked_recommendations`.
5. Saves external request with status `injected`.
6. Saves recommendation.
7. Persists state, metrics, runtime status, and events.

`DundeeEnv.inject_external_request(request)`:

- Builds internal `SimulationRequest`.
- Adds it to `self.requests`.
- Increments `requests_seen_total`.
- Sets `latest_external_request_id`.
- Records `external_request_injected`.

Important: injection adds the request to runtime state, but it does not immediately start charging. Allocation and session start occur during `DundeeEnv.step()` through `_allocate_pending_requests` and `_start_session` or `_enqueue_request`.

## Dashboard-Visible State

The dashboard-visible state comes from `RuntimeStorage`:

- map station data from `StateSnapshot.stations`
- transformer markers from `StateSnapshot.transformers`
- live feed from `StateSnapshot.active_requests`, `queued_requests`, `active_sessions`, and recent `RuntimeEvent`s
- recommendation panel from recent `RecommendationResponse`s
- metrics charts from `MetricsSnapshot` history
- latest external request payload from `external_requests`

