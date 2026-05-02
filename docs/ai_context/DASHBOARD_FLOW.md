# Dashboard Flow

The dashboard reads runtime storage directly. It does not call FastAPI for map/feed/recommendation panels.

## Entry Point

`dashboards/sim_dashboard/app.py`

- Imports `RuntimeManager` from `services.sim_runtime.runtime_manager`.
- Imports `RuntimeStorage` from `services.sim_runtime.storage`.
- Sets `REPO_ROOT = Path(__file__).resolve().parents[2]`.

## Data Loading

`load_runtime_data(repo_root)`:

- creates `RuntimeStorage(repo_root)`
- reads:
  - `state = storage.load_latest_state()`
  - `metrics = storage.load_latest_metrics()`
  - `metric_history = storage.get_metrics_history(limit=288)`
  - `recommendations = storage.get_recent_recommendations(limit=20)`
  - `external_requests = storage.get_recent_external_requests(limit=20)`
  - `events = storage.get_recent_events(limit=300)`
  - `status = storage.load_runtime_status()`

## Runtime Controls

`run_sidebar_controls(runtime, status)`:

- Builds Streamlit controls for day, hour, policy, runtime mode, demand multiplier, warm start, and loop interval.
- Calls `RuntimeManager.start`, `start_loop`, `stop_loop`, or `tick`.
- The busy afternoon demo calls `runtime.start(preset="busy_afternoon")` and `runtime.start_loop(interval_seconds=1.0)`.

## Map Panel

`render_map(state)`:

- Builds `station_df` from `state.stations`.
- Builds `transformer_df` from `state.transformers`.
- Calls `build_map(station_df, transformer_df)`.
- Uses pydeck `ScatterplotLayer` for stations and transformers if available.
- Station colors come from `station_color(row)`:
  - red for `queue_length >= 3`
  - amber for `queue_length >= 1` or `utilization >= 0.75`
  - green otherwise
- Fallback uses `st.map` and station dataframe columns.

Note: the transformer pydeck layer uses `get_position="[longitude, latitude]"`, but `TransformerStateSnapshot` does not define latitude/longitude in `packages/ev_core/src/ev_core/contracts/responses.py`. Whether pydeck renders transformer markers correctly is not verified.

## Live Feed

In `main()`:

- `active_df` is built from `state.active_requests + state.queued_requests + state.active_sessions`.
- Current requests table shows:
  - `request_id`
  - `source_type`
  - `status`
  - `zone_id`
  - `station_id`
  - `requested_energy_kwh`
  - `latest_finish_ts`
- `event_df` is built from recent runtime events and shows:
  - `simulated_timestamp`
  - `event_type`
  - `source_type`
  - `request_id`
  - `station_id`
  - `zone_id`
  - `summary`
- Latest external payload is shown from `external_requests`.

## Recommendation Panel

In `main()`:

- Uses `recommendations` from `RuntimeStorage.get_recent_recommendations`.
- Takes `latest = recommendations[-1]`.
- Shows `latest.top_recommendation` as JSON.
- Shows `latest.alternatives` as a dataframe.
- Shows `latest.debug_reasoning_summary`.
- Shows `latest.congestion_note` if present.

## Metrics Panels

In `main()`:

- Overview metrics come from `state` and `metrics`.
- Time-series chart uses `metric_history`.
- Transformer load chart unfolds `row["transformer_loading_kw"]`.
- Recent arrivals chart is built by `build_recent_arrival_chart(events)`, counting:
  - `replay_request_arrived`
  - `synthetic_request_arrived`
  - `external_request_injected`
- Requests by zone uses `metrics.requests_by_zone`.

