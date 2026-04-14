"""Streamlit dashboard for the standalone Dundee simulator runtime."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.runtime_manager import RuntimeManager  # noqa: E402
from services.sim_runtime.storage import RuntimeStorage  # noqa: E402


def load_runtime_data(repo_root: Path):
    storage = RuntimeStorage(repo_root)
    state = storage.load_latest_state()
    metrics = storage.load_latest_metrics()
    metric_history = storage.get_metrics_history(limit=288)
    recommendations = storage.get_recent_recommendations(limit=20)
    external_requests = storage.get_recent_external_requests(limit=20)
    events = storage.get_recent_events(limit=300)
    status = storage.load_runtime_status()
    return storage, state, metrics, metric_history, recommendations, external_requests, events, status


def station_color(row: pd.Series) -> list[int]:
    if row["queue_length"] >= 3:
        return [220, 38, 38, 200]
    if row["queue_length"] >= 1 or row["utilization"] >= 0.75:
        return [245, 158, 11, 200]
    return [22, 163, 74, 180]


def build_map(station_df: pd.DataFrame, transformer_df: pd.DataFrame):
    station_df = station_df.copy()
    station_df["color"] = station_df.apply(station_color, axis=1)
    transformer_df = transformer_df.copy()
    transformer_df["color"] = [[37, 99, 235, 220] for _ in range(len(transformer_df))]
    return {
        "stations": station_df,
        "transformers": transformer_df,
    }


def render_dataframe(frame: pd.DataFrame) -> None:
    """Render dataframes across older and newer Streamlit versions."""

    try:
        st.dataframe(frame, use_container_width=True)
    except TypeError:
        st.dataframe(frame)


def enable_auto_refresh(interval_seconds: int) -> None:
    """Reload the dashboard page on a lightweight timer."""

    components.html(
        (
            "<script>"
            f"setTimeout(function() {{ window.parent.location.reload(); }}, {max(interval_seconds, 1) * 1000});"
            "</script>"
        ),
        height=0,
        width=0,
    )


def build_recent_arrival_chart(events) -> pd.DataFrame:
    arrival_types = {"replay_request_arrived", "synthetic_request_arrived", "external_request_injected"}
    rows = [
        event.model_dump(mode="json")
        for event in events
        if event.event_type in arrival_types
    ]
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame["simulated_timestamp"] = pd.to_datetime(frame["simulated_timestamp"])
    frame["sim_hour"] = frame["simulated_timestamp"].dt.floor("h")
    grouped = (
        frame.groupby(["sim_hour", "event_type"], as_index=False)
        .size()
        .rename(columns={"size": "arrival_count"})
    )
    pivot = grouped.pivot_table(
        index="sim_hour",
        columns="event_type",
        values="arrival_count",
        aggfunc="sum",
        fill_value=0,
    )
    return pivot.tail(24)


def run_sidebar_controls(runtime: RuntimeManager, status: dict) -> None:
    st.sidebar.header("Demo Controls")
    refresh_seconds = st.sidebar.selectbox("Auto-refresh", [1, 2], index=0)
    enable_auto_refresh(int(refresh_seconds))

    preset = st.sidebar.selectbox("Preset", ["Custom", "Busy Afternoon Demo"])
    use_preset = preset == "Busy Afternoon Demo"
    day_value = "2024-06-10"
    hour_value = 15 if use_preset else 0
    minute_value = 0
    policy_value = "overload_aware"
    mode_value = "hybrid" if use_preset else "replay"
    multiplier_value = 1.35 if use_preset else 1.0
    warm_start_value = 4 if use_preset else 0

    replay_day = st.sidebar.text_input("Start day", value=day_value)
    start_hour = st.sidebar.selectbox("Start hour", list(range(24)), index=hour_value)
    start_minute = st.sidebar.selectbox("Start minute", [0, 15, 30, 45], index=[0, 15, 30, 45].index(minute_value))
    policy_mode = st.sidebar.selectbox("Policy", ["overload_aware", "cost_aware", "greedy_fastest_service", "random"], index=["overload_aware", "cost_aware", "greedy_fastest_service", "random"].index(policy_value))
    runtime_mode = st.sidebar.selectbox("Runtime mode", ["replay", "synthetic", "hybrid"], index=["replay", "synthetic", "hybrid"].index(mode_value))
    demand_multiplier = st.sidebar.selectbox("Demand multiplier", [0.75, 1.0, 1.25, 1.35, 1.5, 1.75], index=[0.75, 1.0, 1.25, 1.35, 1.5, 1.75].index(multiplier_value))
    warm_start_hours = st.sidebar.selectbox("Warm-start horizon", [0, 2, 4, 8], index=[0, 2, 4, 8].index(warm_start_value))
    loop_interval = st.sidebar.selectbox("Loop interval (s)", [1.0, 1.5, 2.0], index=0)

    if st.sidebar.button("Start Runtime"):
        runtime.start(
            replay_day=replay_day,
            start_hour=int(start_hour),
            start_minute=int(start_minute),
            policy_mode=policy_mode,
            runtime_mode=runtime_mode,
            demand_multiplier=float(demand_multiplier),
            warm_start_hours=int(warm_start_hours),
            preset="busy_afternoon" if use_preset else None,
        )
        st.sidebar.success("Runtime started.")

    if st.sidebar.button("Start Loop"):
        if runtime.get_latest_state() is None:
            runtime.start(
                replay_day=replay_day,
                start_hour=int(start_hour),
                start_minute=int(start_minute),
                policy_mode=policy_mode,
                runtime_mode=runtime_mode,
                demand_multiplier=float(demand_multiplier),
                warm_start_hours=int(warm_start_hours),
                preset="busy_afternoon" if use_preset else None,
            )
        runtime.start_loop(interval_seconds=float(loop_interval))
        st.sidebar.success("Loop started.")

    if st.sidebar.button("Stop Loop"):
        runtime.stop_loop()
        st.sidebar.info("Loop stop requested.")

    if st.sidebar.button("Tick Once"):
        runtime.tick(steps=1)
        st.sidebar.success("Advanced one 15-minute simulation slot.")

    if st.sidebar.button("Busy Afternoon Demo"):
        runtime.start(preset="busy_afternoon")
        runtime.start_loop(interval_seconds=1.0)
        st.sidebar.success("Busy Afternoon Demo started in loop mode.")

    st.sidebar.markdown("**Runtime status**")
    st.sidebar.json(status)


def render_map(state) -> None:
    station_df = pd.DataFrame([station.model_dump(mode="json") for station in state.stations])
    transformer_df = pd.DataFrame([transformer.model_dump(mode="json") for transformer in state.transformers])
    map_data = build_map(station_df, transformer_df)
    try:
        import pydeck as pdk

        station_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data["stations"],
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius="120 + cp_count_total * 15",
            pickable=True,
            tooltip=True,
        )
        transformer_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data["transformers"],
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius=220,
            pickable=True,
        )
        view_state = pdk.ViewState(
            latitude=float(station_df["latitude"].mean()),
            longitude=float(station_df["longitude"].mean()),
            zoom=11.5,
            pitch=0,
        )
        st.pydeck_chart(
            pdk.Deck(
                map_style="light",
                initial_view_state=view_state,
                layers=[station_layer, transformer_layer],
                tooltip={
                    "html": (
                        "<b>{station_name}</b><br/>"
                        "station_id: {station_id}<br/>"
                        "zone_id: {zone_id}<br/>"
                        "transformer_id: {transformer_id}<br/>"
                        "cp_count_total: {cp_count_total}<br/>"
                        "capacity_kw: {station_capacity_kw_assumed}<br/>"
                        "queue: {queue_length}<br/>"
                        "utilization: {utilization}<br/>"
                        "headroom_kw: {transformer_headroom_kw}"
                    )
                },
            )
        )
        st.caption("Station colors reflect queue severity / utilization. Blue markers indicate synthetic transformers.")
    except Exception:
        st.map(station_df.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]])
        render_dataframe(station_df[["station_name", "station_id", "zone_id", "transformer_id", "queue_length", "utilization"]])


def main() -> None:
    st.set_page_config(page_title="Dundee Simulator Dashboard", layout="wide")
    st.title("Dundee Simulator Dashboard")
    st.caption("Standalone EV-side runtime visualization outside apps/**.")

    runtime = RuntimeManager(REPO_ROOT)
    _, state, metrics, metric_history, recommendations, external_requests, events, status = load_runtime_data(REPO_ROOT)
    run_sidebar_controls(runtime, status)

    if state is None or metrics is None:
        st.warning("No runtime snapshot found yet. Use the sidebar to start the Dundee simulator runtime.")
        return

    overview = st.columns(7)
    overview[0].metric("Sim Time", str(state.simulated_timestamp))
    overview[1].metric("Policy", state.active_policy)
    overview[2].metric("Mode", state.runtime_mode)
    overview[3].metric("Loop", "Running" if state.loop_running else "Stopped")
    overview[4].metric("Active Requests", metrics.active_request_count)
    overview[5].metric("Queued", metrics.queued_request_count)
    overview[6].metric("Active Sessions", metrics.active_session_count)

    secondary = st.columns(6)
    secondary[0].metric("Completed", metrics.completed_requests_total)
    secondary[1].metric("Missed", metrics.missed_requests_total)
    secondary[2].metric("Overload Events", metrics.overload_event_count)
    secondary[3].metric("Replay Cursor", f"{state.replay_cursor}/{state.replay_total}")
    secondary[4].metric("Demand x", f"{state.demand_multiplier:.2f}")
    secondary[5].metric("Warm-start", f"{state.warm_start_minutes} min")

    st.subheader("Map")
    render_map(state)

    latest_external = pd.DataFrame([request.model_dump(mode="json") for request in external_requests[::-1]]) if external_requests else pd.DataFrame()
    if not latest_external.empty:
        st.success(f"Latest external_live request: {latest_external.iloc[0]['client_request_id']}")

    left, right = st.columns([1.15, 0.85])

    with left:
        st.subheader("Live Feed")
        active_df = pd.DataFrame([request.model_dump(mode="json") for request in state.active_requests + state.queued_requests + state.active_sessions])
        if not active_df.empty:
            st.markdown("**Current requests and charging sessions**")
            render_dataframe(active_df[["request_id", "source_type", "status", "zone_id", "station_id", "requested_energy_kwh", "latest_finish_ts"]])
        else:
            st.info("No active or queued requests in the current snapshot.")

        event_df = pd.DataFrame([event.model_dump(mode="json") for event in events])
        if not event_df.empty:
            st.markdown("**Recent runtime events**")
            render_dataframe(event_df[["simulated_timestamp", "event_type", "source_type", "request_id", "station_id", "zone_id", "summary"]].tail(40))

        if not latest_external.empty:
            st.markdown("**Latest external_live request payload**")
            st.json(latest_external.iloc[0].to_dict())

    with right:
        st.subheader("Recommendation Panel")
        if recommendations:
            latest = recommendations[-1]
            if latest.top_recommendation is not None:
                st.markdown("**Top recommendation**")
                st.json(latest.top_recommendation.model_dump(mode="json"))
            if latest.alternatives:
                st.markdown("**Alternatives**")
                render_dataframe(pd.DataFrame([option.model_dump(mode="json") for option in latest.alternatives]))
            st.markdown("**Reasoning summary**")
            st.write(latest.debug_reasoning_summary)
            if latest.congestion_note:
                st.info(latest.congestion_note)
        else:
            st.info("No recommendations have been recorded yet.")

    st.subheader("Metrics")
    history_df = pd.DataFrame([item.model_dump(mode="json") for item in metric_history])
    if not history_df.empty:
        history_df["simulated_timestamp"] = pd.to_datetime(history_df["simulated_timestamp"])
        st.line_chart(
            history_df.set_index("simulated_timestamp")[
                ["active_request_count", "queued_request_count", "completed_requests_total", "missed_requests_total"]
            ]
        )
        transformer_rows = []
        for _, row in history_df.iterrows():
            for transformer_id, load_kw in row["transformer_loading_kw"].items():
                transformer_rows.append(
                    {
                        "simulated_timestamp": row["simulated_timestamp"],
                        "transformer_id": transformer_id,
                        "load_kw": load_kw,
                    }
                )
        if transformer_rows:
            transformer_history = pd.DataFrame(transformer_rows)
            transformer_pivot = transformer_history.pivot_table(
                index="simulated_timestamp",
                columns="transformer_id",
                values="load_kw",
                aggfunc="last",
            )
            st.line_chart(transformer_pivot)

    recent_arrivals = build_recent_arrival_chart(events)
    if not recent_arrivals.empty:
        st.markdown("**Requests per recent simulated hour**")
        st.bar_chart(recent_arrivals)

    st.markdown("**Requests by zone**")
    zone_df = pd.DataFrame(
        [{"zone_id": zone_id, "request_count": count} for zone_id, count in metrics.requests_by_zone.items()]
    )
    render_dataframe(zone_df)


if __name__ == "__main__":
    main()
