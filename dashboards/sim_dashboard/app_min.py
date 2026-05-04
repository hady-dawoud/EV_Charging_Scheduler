"""Minimal Streamlit dashboard for the Dundee simulator runtime."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.runtime_manager import RuntimeManager  # noqa: E402
from services.sim_runtime.storage import RuntimeStorage  # noqa: E402


def to_dict_list(items):
    return [item.model_dump(mode="json") for item in items]


def render_dataframe(title: str, frame: pd.DataFrame) -> None:
    st.subheader(title)

    if frame.empty:
        st.info("No data.")
        return

    st.dataframe(frame, use_container_width=True)

def build_metric_history_frame(metric_history) -> pd.DataFrame:
    rows = [item.model_dump(mode="json") for item in metric_history]

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)

    if "simulated_timestamp" in frame.columns:
        frame["simulated_timestamp"] = pd.to_datetime(frame["simulated_timestamp"])

    return frame


def build_transformer_load_frame(history_df: pd.DataFrame) -> pd.DataFrame:
    if history_df.empty or "transformer_loading_kw" not in history_df.columns:
        return pd.DataFrame()

    rows = []

    for _, row in history_df.iterrows():
        timestamp = row["simulated_timestamp"]
        loading = row.get("transformer_loading_kw", {})

        if not isinstance(loading, dict):
            continue

        for transformer_id, load_kw in loading.items():
            rows.append(
                {
                    "simulated_timestamp": timestamp,
                    "transformer_id": transformer_id,
                    "load_kw": load_kw,
                }
            )

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)

    return frame.pivot_table(
        index="simulated_timestamp",
        columns="transformer_id",
        values="load_kw",
        aggfunc="last",
    )


def render_simple_charts(metric_history) -> None:
    st.subheader("Runtime Charts")

    history_df = build_metric_history_frame(metric_history)

    if history_df.empty:
        st.info("No metric history yet. Tick the runtime a few times.")
        return

    history_df = history_df.sort_values("simulated_timestamp")

    request_cols = [
        "active_request_count",
        "queued_request_count",
        "active_session_count",
    ]

    available_request_cols = [
        col for col in request_cols if col in history_df.columns
    ]

    if available_request_cols:
        st.markdown("**Requests and active charging sessions**")
        st.line_chart(
            history_df.set_index("simulated_timestamp")[available_request_cols]
        )

    total_cols = [
        "completed_requests_total",
        "missed_requests_total",
        "overload_event_count",
    ]

    available_total_cols = [
        col for col in total_cols if col in history_df.columns
    ]

    if available_total_cols:
        st.markdown("**Completed / missed / overload totals**")
        st.line_chart(
            history_df.set_index("simulated_timestamp")[available_total_cols]
        )

    transformer_load_df = build_transformer_load_frame(history_df)

    if not transformer_load_df.empty:
        st.markdown("**Transformer loading kW**")
        st.line_chart(transformer_load_df)

def load_runtime(repo_root: Path):
    storage = RuntimeStorage(repo_root)

    state = storage.load_latest_state()
    metrics = storage.load_latest_metrics()
    metric_history = storage.get_metrics_history(limit=288)
    events = storage.get_recent_events(limit=80)
    recommendations = storage.get_recent_recommendations(limit=5)
    external_requests = storage.get_recent_external_requests(limit=5)
    status = storage.load_runtime_status()

    return state, metrics, metric_history, events, recommendations, external_requests, status


def main() -> None:
    st.set_page_config(
        page_title="Dundee Runtime - Minimal",
        layout="wide",
    )

    st.title("Dundee Simulator Runtime - Minimal Dashboard")
    st.caption("Minimal read/control dashboard for debugging runtime state.")

    runtime = RuntimeManager(REPO_ROOT)
    state, metrics, metric_history, events, recommendations, external_requests, status = load_runtime(REPO_ROOT)

    st.sidebar.header("Controls")

    if st.sidebar.button("Refresh"):
        st.rerun()

    st.sidebar.subheader("Start")

    start_day = st.sidebar.text_input("Replay day", value="2024-06-10")
    start_hour = st.sidebar.selectbox("Start hour", list(range(24)), index=15)
    policy_mode = st.sidebar.selectbox(
        "Policy",
        ["overload_aware", "cost_aware", "greedy_fastest_service", "random"],
        index=0,
    )

    if st.sidebar.button("Start Runtime"):
        runtime.start(
            replay_day=start_day,
            start_hour=int(start_hour),
            start_minute=0,
            policy_mode=policy_mode,
            runtime_mode="replay",
            demand_multiplier=1.0,
            warm_start_hours=0,
        )
        st.rerun()

    if st.sidebar.button("Tick Once"):
        runtime.tick(steps=1)
        st.rerun()

    if st.sidebar.button("Tick 4 Steps"):
        runtime.tick(steps=4)
        st.rerun()

    if st.sidebar.button("Start Busy Demo"):
        runtime.start(preset="busy_afternoon")
        st.rerun()

    if st.sidebar.button("Start Loop"):
        runtime.start_loop(interval_seconds=1.0)
        st.rerun()

    if st.sidebar.button("Stop Loop"):
        runtime.stop_loop()
        st.rerun()

    st.sidebar.subheader("Raw Status")
    st.sidebar.json(status)

    if state is None or metrics is None:
        st.warning("No runtime snapshot found. Start the runtime first.")
        return

    top = st.columns(6)
    top[0].metric("Running", str(status.get("running", "unknown")))
    top[1].metric("Loop", "Running" if state.loop_running else "Stopped")
    top[2].metric("Sim Time", str(state.simulated_timestamp))
    top[3].metric("Policy", state.active_policy)
    top[4].metric("Mode", state.runtime_mode)
    top[5].metric("Replay", f"{state.replay_cursor}/{state.replay_total}")

    kpis = st.columns(6)
    kpis[0].metric("Active Requests", metrics.active_request_count)
    kpis[1].metric("Queued", metrics.queued_request_count)
    kpis[2].metric("Charging", metrics.active_session_count)
    kpis[3].metric("Completed", metrics.completed_requests_total)
    kpis[4].metric("Missed", metrics.missed_requests_total)
    kpis[5].metric("Overloads", metrics.overload_event_count)

    st.divider()

    render_scenario_summary(state, metrics)

    st.divider()

    st.divider()

    render_simple_charts(metric_history)

    st.divider()

    active_items = (
        to_dict_list(state.active_requests)
        + to_dict_list(state.queued_requests)
        + to_dict_list(state.active_sessions)
    )

    active_df = pd.DataFrame(active_items)
    if not active_df.empty:
        keep_cols = [
            "request_id",
            "client_request_id",
            "source_type",
            "status",
            "arrival_ts",
            "latest_finish_ts",
            "station_name",
            "zone_id",
            "requested_energy_kwh",
            "remaining_minutes",
        ]
        active_df = active_df[[col for col in keep_cols if col in active_df.columns]]

    render_dataframe("Current Requests / Sessions", active_df)

    station_df_full = pd.DataFrame(to_dict_list(state.stations))

    if not station_df_full.empty:
        st.subheader("Station Map")

        map_df = station_df_full.rename(
            columns={
                "latitude": "lat",
                "longitude": "lon",
            }
        )

        map_df = map_df.dropna(subset=["lat", "lon"])

        if not map_df.empty:
            st.map(
                map_df[
                    [
                        "lat",
                        "lon",
                        "station_name",
                        "zone_id",
                        "transformer_id",
                        "active_sessions",
                        "queue_length",
                        "utilization",
                    ]
                ]
            )
        else:
            st.info("No valid station coordinates available.")

    station_df = station_df_full.copy()

    if not station_df.empty:
        station_cols = [
            "station_name",
            "zone_id",
            "transformer_id",
            "cp_count_total",
            "active_sessions",
            "queue_length",
            "utilization",
            "estimated_wait_minutes",
            "transformer_headroom_kw",
        ]
        station_df = station_df[[col for col in station_cols if col in station_df.columns]]
        station_df = station_df.sort_values(
            by=["queue_length", "active_sessions", "utilization"],
            ascending=False,
        )

    render_dataframe("Stations", station_df)

    transformer_df = pd.DataFrame(to_dict_list(state.transformers))
    if not transformer_df.empty:
        transformer_cols = [
            "transformer_name",
            "zone_id",
            "capacity_kw",
            "background_load_kw",
            "ev_load_kw",
            "net_load_kw",
            "headroom_kw",
            "overload",
        ]
        transformer_df = transformer_df[[col for col in transformer_cols if col in transformer_df.columns]]
        transformer_df = transformer_df.sort_values(by="net_load_kw", ascending=False)

    render_dataframe("Transformers", transformer_df)

    event_df = pd.DataFrame(to_dict_list(events))
    if not event_df.empty:
        event_cols = [
            "simulated_timestamp",
            "event_type",
            "source_type",
            "request_id",
            "station_id",
            "zone_id",
            "summary",
        ]
        event_df = event_df[[col for col in event_cols if col in event_df.columns]]
        event_df = event_df.tail(40)

    render_dataframe("Recent Events", event_df)

    st.subheader("Latest Recommendation")

    if recommendations:
        latest = recommendations[-1]
        latest_json = latest.model_dump(mode="json")

        top_rec = latest_json.get("top_recommendation")
        alternatives = latest_json.get("alternatives", [])

        if top_rec:
            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Station", top_rec.get("station_name", "Unknown"))
            c2.metric("Wait", f"{top_rec.get('estimated_wait_minutes', 0)} min")
            c3.metric("Duration", f"{top_rec.get('estimated_duration_minutes', 0)} min")
            c4.metric("Cost", f"£{top_rec.get('estimated_cost_gbp', 0):.2f}")

            st.markdown("**Reason tags**")
            st.write(", ".join(top_rec.get("reason_tags", [])))

            st.markdown("**Top recommendation details**")
            st.dataframe(
                pd.DataFrame([top_rec]),
                use_container_width=True,
            )
        else:
            st.info("No top recommendation in the latest response.")

        if alternatives:
            st.markdown("**Alternatives**")
            st.dataframe(
                pd.DataFrame(alternatives),
                use_container_width=True,
            )

        with st.expander("Raw recommendation JSON"):
            st.json(latest_json)
    else:
        st.info("No recommendations yet.")

def render_scenario_summary(state, metrics) -> None:
    st.subheader("Scenario Summary")

    busiest_station = None
    if state.stations:
        busiest_station = max(
            state.stations,
            key=lambda station: (
                station.active_sessions,
                station.queue_length,
                station.utilization,
            ),
        )

    busiest_transformer = None
    if state.transformers:
        busiest_transformer = max(
            state.transformers,
            key=lambda transformer: transformer.net_load_kw,
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Requests Seen", metrics.requests_seen_total)
    c2.metric("Completed", metrics.completed_requests_total)
    c3.metric("Missed", metrics.missed_requests_total)
    c4.metric("Overloads", metrics.overload_event_count)

    c5, c6 = st.columns(2)

    if busiest_station is not None:
        c5.markdown("**Busiest Station**")
        c5.write(busiest_station.station_name)
        c5.write(
            f"{busiest_station.active_sessions} active sessions, "
            f"{busiest_station.queue_length} queued, "
            f"{busiest_station.utilization:.0%} utilization"
        )

    if busiest_transformer is not None:
        loading_pct = (
            busiest_transformer.net_load_kw / busiest_transformer.capacity_kw
        ) * 100

        c6.markdown("**Highest Loaded Transformer**")
        c6.write(busiest_transformer.transformer_name)
        c6.write(
            f"{busiest_transformer.net_load_kw:.1f} / "
            f"{busiest_transformer.capacity_kw:.1f} kW "
            f"({loading_pct:.1f}%)"
        )

if __name__ == "__main__":
    main()