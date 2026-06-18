"""Streamlit dashboard for the standalone Dundee simulator runtime."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable, TypeVar

import pandas as pd
from pydantic import BaseModel, ValidationError

try:
    import streamlit as st
except ImportError:  # pragma: no cover - exercised by smoke tests without dashboard deps
    st = None

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.runtime_manager import RuntimeManager  # noqa: E402
from services.sim_runtime.storage import RuntimeStorage  # noqa: E402
from ev_core.contracts.requests import ExternalChargingRequest  # noqa: E402
from ev_core.contracts.responses import RecommendationResponse  # noqa: E402

PydanticRecord = TypeVar("PydanticRecord", bound=BaseModel)
RECENT_REQUEST_LIMIT = 20
RECENT_RESPONSE_LIMIT = 20


def load_runtime_data(repo_root: Path):
    storage = RuntimeStorage(repo_root)
    state = storage.load_latest_state()
    metrics = storage.load_latest_metrics()
    metric_history = storage.get_metrics_history(limit=96)
    external_requests = load_recent_external_requests(storage)
    recommendations = load_recent_recommendations(storage)
    events = storage.get_recent_events(limit=80)
    status = storage.load_runtime_status()
    return storage, state, metrics, metric_history, recommendations, external_requests, events, status


def load_recent_external_requests(storage: RuntimeStorage) -> list[ExternalChargingRequest]:
    external_requests = storage.get_recent_external_requests(limit=RECENT_REQUEST_LIMIT)

    if external_requests:
        return external_requests

    return read_json_records(
        storage.artifacts.latest_external_requests_path,
        ExternalChargingRequest,
        limit=RECENT_REQUEST_LIMIT,
    )


def load_recent_recommendations(storage: RuntimeStorage) -> list[RecommendationResponse]:
    recommendations = storage.get_recent_recommendations(limit=RECENT_RESPONSE_LIMIT)

    if recommendations:
        return recommendations

    return read_json_records(
        storage.artifacts.recent_recommendations_path,
        RecommendationResponse,
        limit=RECENT_RESPONSE_LIMIT,
    )


def read_json_records(path: Path, model_type: type[PydanticRecord], *, limit: int) -> list[PydanticRecord]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Runtime JSON artifact is malformed: {path}") from exc

    if not isinstance(payload, list):
        raise RuntimeError(f"Runtime JSON artifact must contain a list: {path}")

    try:
        records = [model_type.model_validate(row) for row in payload]
    except ValidationError as exc:
        raise RuntimeError(f"Runtime JSON artifact does not match {model_type.__name__}: {path}") from exc

    return records[-limit:]


def build_status_panel_values(state, metrics, status: dict) -> dict:
    return {
        "runtime_status": str(status.get("runtime_status", "unknown")),
        "simulated_timestamp": None if state is None else state.simulated_timestamp,
        "recommendation_policy": str(status.get("recommendation_policy_name", "unknown")),
        "pricing_model": str(status.get("pricing_model", "unknown")),
        "dynamic_pricing_enabled": bool(status.get("dynamic_pricing_enabled", False)),
        "routing_provider": str(status.get("routing_provider_name", "unknown")),
        "osmnx_graph_exists": bool(status.get("osmnx_graph_exists", False)),
    }


def render_dataframe(frame: pd.DataFrame) -> None:
    """Render dataframes across older and newer Streamlit versions."""

    try:
        st.dataframe(frame, use_container_width=True)
    except TypeError:
        st.dataframe(frame)


def metric_delta(completed_count: int, missed_count: int) -> str:
    total_outcomes = completed_count + missed_count

    if total_outcomes == 0:
        return "No finished requests yet"

    completion_rate = completed_count / total_outcomes
    return f"{completion_rate:.0%} completed"


def kw_text(kw_amount: float | None) -> str:
    if kw_amount is None:
        return "n/a"

    return f"{kw_amount:.1f} kW"


def percentage_text(ratio: float | None) -> str:
    if ratio is None:
        return "n/a"

    return f"{ratio:.0%}"


def model_rows(snapshots) -> list[dict]:
    return [snapshot.model_dump(mode="json") for snapshot in snapshots]


def short_identifier(identifier: str | None) -> str:
    if identifier is None or not identifier:
        return "n/a"

    if len(identifier) <= 18:
        return identifier

    return f"{identifier[:10]}...{identifier[-6:]}"


def gbp_text(amount: float | None) -> str:
    if amount is None:
        return "n/a"

    return f"GBP {amount:.2f}"


def minutes_text(minutes: int | None) -> str:
    if minutes is None:
        return "n/a"

    return f"{minutes} min"


def score_text(score: float | None) -> str:
    if score is None:
        return "n/a"

    return f"{score:.3f}"


def station_activity_frame(state, external_requests: Iterable[Any] = (), recommendations: Iterable[Any] = ()) -> pd.DataFrame:
    activity_by_station = station_activity_by_station(state, external_requests, recommendations)
    station_rows = [station_activity_row(station, activity_by_station) for station in state.stations]

    if not station_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(station_rows)
    return frame.sort_values(
        by=["Queued count", "Active / Charging count", "Utilization ratio"],
        ascending=[False, False, False],
    ).drop(columns=["Utilization ratio"])


def station_activity_row(station, activity_by_station: dict[str, dict]) -> dict:
    station_activity = activity_by_station.get(station.station_id, {})
    active_count = activity_count_or_snapshot(station_activity, station, "active")
    queued_count = activity_count_or_snapshot(station_activity, station, "queued")
    assigned_request_ids = station_request_ids_text(station, station_activity)
    return {
        "Station": station.station_name,
        "Zone": station.zone_id,
        "Status": station_status_text(station, active_count, queued_count, station_activity),
        "Active / Charging count": active_count,
        "Queued count": queued_count,
        "Assigned / active request IDs": assigned_request_ids,
        "Utilization": percentage_text(station.utilization),
        "Utilization ratio": station.utilization,
        "Estimated wait": minutes_text(station.estimated_wait_minutes),
        "Headroom": kw_text(station.transformer_headroom_kw),
    }


def station_activity_by_station(state, external_requests: Iterable[Any], recommendations: Iterable[Any]) -> dict[str, dict]:
    station_lookup = station_identifier_lookup(state.stations)
    activity_by_station: dict[str, dict] = {}

    add_station_records(activity_by_station, station_lookup, state.active_sessions, "active")
    add_station_records(activity_by_station, station_lookup, getattr(state, "charging_requests", []), "active")
    add_station_records(activity_by_station, station_lookup, getattr(state, "sessions", []), "active")
    add_station_records(activity_by_station, station_lookup, state.queued_requests, "queued")
    add_status_records(activity_by_station, station_lookup, state.active_requests)
    add_status_records(activity_by_station, station_lookup, external_requests)
    add_status_records(activity_by_station, station_lookup, recommendations)
    return activity_by_station


def station_identifier_lookup(stations) -> dict[str, str]:
    station_lookup = {}
    for station in stations:
        station_lookup[station.station_id] = station.station_id
        station_lookup[normalize_station_name(station.station_name)] = station.station_id
    return station_lookup


def add_station_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records, activity_kind: str) -> None:
    for record in records:
        station_id = matched_station_id(record, station_lookup)
        if station_id is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, {"active_ids": [], "queued_ids": [], "assigned_ids": []})
        record_id = record_request_id(record)
        if activity_kind == "queued":
            station_activity["queued_ids"].append(record_id)
        else:
            station_activity["active_ids"].append(record_id)


def add_status_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records) -> None:
    for record in records:
        station_id = matched_station_id(record, station_lookup)
        activity_kind = record_activity_kind(record)
        if station_id is None or activity_kind is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, {"active_ids": [], "queued_ids": [], "assigned_ids": []})
        station_activity[f"{activity_kind}_ids"].append(record_request_id(record))


def matched_station_id(record, station_lookup: dict[str, str]) -> str | None:
    station_id = first_record_value(
        record,
        "station_id",
        "assigned_station_id",
        "selected_station_id",
        "recommended_station_id",
    )
    if station_id in station_lookup:
        return station_lookup[station_id]

    top_recommendation = record_value(record, "top_recommendation")
    top_station_id = record_value(top_recommendation, "station_id")
    if top_station_id in station_lookup:
        return station_lookup[top_station_id]

    station_name = first_record_value(
        record,
        "station_name",
        "assigned_station_name",
        "selected_station_name",
        "recommended_station_name",
        "selected_location_name",
    )
    normalized_name = normalize_station_name(station_name)
    if normalized_name in station_lookup:
        return station_lookup[normalized_name]

    top_station_name = normalize_station_name(record_value(top_recommendation, "station_name"))
    return station_lookup.get(top_station_name)


def record_activity_kind(record) -> str | None:
    status = str(
        first_record_value(
            record,
            "status",
            "session_status",
            "charging_status",
            "reservation_status",
        )
        or ""
    ).lower()

    if status in {"charging", "active", "started", "in_progress"}:
        return "active"
    if status in {"queued", "waiting"}:
        return "queued"
    if status in {"assigned", "reserved", "confirmed"}:
        return "assigned"
    return None


def first_record_value(record, *field_names: str):
    for field_name in field_names:
        field_value = record_value(record, field_name)
        if field_value not in (None, ""):
            return field_value
        metadata_value = record_metadata_value(record, field_name)
        if metadata_value not in (None, ""):
            return metadata_value
    return None


def record_value(record, field_name: str):
    if record is None:
        return None
    if isinstance(record, dict):
        return record.get(field_name)
    return getattr(record, field_name, None)


def record_metadata_value(record, field_name: str):
    metadata = record_value(record, "metadata")
    if isinstance(metadata, dict):
        return metadata.get(field_name)
    return None


def normalize_station_name(station_name) -> str:
    if station_name is None:
        return ""
    return str(station_name).strip().casefold()


def record_request_id(record) -> str:
    request_id = first_record_value(record, "request_id", "client_request_id", "session_id", "reservation_id")
    return str(request_id) if request_id else "unknown"


def activity_count_or_snapshot(station_activity: dict, station, activity_kind: str) -> int:
    activity_ids = station_activity.get(f"{activity_kind}_ids", [])
    if activity_ids:
        return len(activity_ids)
    if activity_kind == "queued":
        return station.queue_length
    return station.active_sessions


def station_request_ids_text(station, station_activity: dict) -> str:
    request_ids = [
        *station_activity.get("active_ids", []),
        *station_activity.get("queued_ids", []),
        *station_activity.get("assigned_ids", []),
    ]

    if not request_ids:
        request_ids = [*station.active_request_ids, *station.queued_request_ids]

    if not request_ids:
        return "—"

    return ", ".join(short_identifier(request_id) for request_id in request_ids)


def station_status_text(station, active_count: int, queued_count: int, station_activity: dict) -> str:
    if getattr(station, "blocked", False):
        return "Blocked"
    if getattr(station, "offline", False):
        return "Offline"
    if getattr(station, "available", True) is False:
        return "Unavailable"
    if active_count > 0:
        return "Charging"
    if queued_count > 0:
        return "Queued"
    if station_activity.get("assigned_ids"):
        return "Active"
    return "Available"


def has_unassigned_mobile_activity(state, external_requests) -> bool:
    runtime_records = [*state.active_requests, *state.queued_requests, *external_requests]
    station_lookup = station_identifier_lookup(state.stations)
    return any(
        is_mobile_record(record)
        and (matched_station_id(record, station_lookup) is None or record_activity_kind(record) is None)
        for record in runtime_records
    )


def is_mobile_record(record) -> bool:
    source_type = str(record_value(record, "source_type") or "").casefold()
    source = str(record_metadata_value(record, "source") or "").casefold()
    channel = str(record_metadata_value(record, "channel") or "").casefold()
    client_request_id = str(record_value(record, "client_request_id") or "").casefold()
    return "mobile" in source_type or "mobile" in source or "mobile" in channel or client_request_id.startswith("mobile_")


def station_pressure_frame(state) -> pd.DataFrame:
    station_rows = [
        {
            "Station": station.station_name,
            "Zone": station.zone_id,
            "Charging": station.active_sessions,
            "Queued": station.queue_length,
            "Utilization": percentage_text(station.utilization),
            "Utilization ratio": station.utilization,
            "Wait": f"{station.estimated_wait_minutes} min",
            "Headroom": kw_text(station.transformer_headroom_kw),
        }
        for station in state.stations
    ]

    if not station_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(station_rows)
    sorted_frame = frame.sort_values(
        by=["Queued", "Charging", "Utilization ratio"],
        ascending=[False, False, False],
    ).head(8)
    return sorted_frame.drop(columns=["Utilization ratio"])


def transformer_pressure_frame(state) -> pd.DataFrame:
    transformer_rows = [
        {
            "Transformer": transformer.transformer_name,
            "Zone": transformer.zone_id,
            "EV load": kw_text(transformer.ev_load_kw),
            "Net load": kw_text(transformer.net_load_kw),
            "Net load kW": transformer.net_load_kw,
            "Headroom": kw_text(transformer.headroom_kw),
            "Overload": "Yes" if transformer.overload else "No",
        }
        for transformer in state.transformers
    ]

    if not transformer_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(transformer_rows)
    sorted_frame = frame.sort_values(by=["Overload", "Net load kW"], ascending=[False, False]).head(6)
    return sorted_frame.drop(columns=["Net load kW"])


def metric_history_frame(metric_history) -> pd.DataFrame:
    history_rows = model_rows(metric_history)

    if not history_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(history_rows)
    frame["simulated_timestamp"] = pd.to_datetime(frame["simulated_timestamp"])
    return frame.sort_values("simulated_timestamp")


def recent_events_frame(events) -> pd.DataFrame:
    event_rows = model_rows(events)

    if not event_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(event_rows)
    visible_columns = [
        "simulated_timestamp",
        "event_type",
        "source_type",
        "station_id",
        "zone_id",
        "summary",
    ]
    return frame[[column for column in visible_columns if column in frame.columns]].tail(25)


def recent_arrivals_frame(events) -> pd.DataFrame:
    arrival_types = {"replay_request_arrived", "synthetic_request_arrived", "external_request_injected"}
    arrival_rows = [
        event.model_dump(mode="json")
        for event in events
        if event.event_type in arrival_types
    ]

    if not arrival_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(arrival_rows)
    frame["simulated_timestamp"] = pd.to_datetime(frame["simulated_timestamp"])
    frame["sim_hour"] = frame["simulated_timestamp"].dt.floor("h")
    grouped = (
        frame.groupby(["sim_hour", "event_type"], as_index=False)
        .size()
        .rename(columns={"size": "arrival_count"})
    )
    return grouped.pivot_table(
        index="sim_hour",
        columns="event_type",
        values="arrival_count",
        aggfunc="sum",
        fill_value=0,
    ).tail(12)


def latest_external_frame(external_requests) -> pd.DataFrame:
    if not external_requests:
        return pd.DataFrame()

    return pd.DataFrame(model_rows(external_requests[::-1]))


def recommendation_matches(external_requests, recommendations) -> list[dict]:
    request_by_client_id = {
        request.client_request_id: request
        for request in external_requests
        if request.client_request_id
    }
    request_by_runtime_id = {
        request.request_id: request
        for request in external_requests
        if request.request_id
    }
    matched_request_ids = set()
    rows = []

    for response in reversed(recommendations):
        request = request_by_client_id.get(response.client_request_id)
        if request is None:
            request = request_by_client_id.get(response.request_id)
        if request is None:
            request = request_by_runtime_id.get(response.request_id)
        if request is not None:
            matched_request_ids.add(id(request))
        rows.append(recommendation_match_row(request, response))

    for request in reversed(external_requests):
        if id(request) not in matched_request_ids:
            rows.append(recommendation_match_row(request, None))

    return rows


def recommendation_match_row(request, response) -> dict:
    top_recommendation = None if response is None else response.top_recommendation
    option_metadata = {} if top_recommendation is None else top_recommendation.metadata
    request_metadata = {} if request is None else request.metadata
    candidate_count = 0 if response is None else len(response.alternatives) + (1 if top_recommendation else 0)
    return {
        "Request time": None if request is None else request.request_timestamp,
        "User": request_metadata.get("user_id", "n/a"),
        "Client request": "n/a" if request is None else short_identifier(request.client_request_id),
        "Runtime request": "n/a" if response is None else short_identifier(response.request_id),
        "Location": selected_location_text(request, response),
        "Need": charging_need_text(request),
        "Policy": recommendation_policy_text(response),
        "Candidates": candidate_count,
        "Candidate stations": candidate_station_names(response),
        "Recommended station": "Unmatched" if top_recommendation is None else top_recommendation.station_name,
        "Score": "n/a" if top_recommendation is None else score_text(top_recommendation.score),
        "Wait": "n/a" if top_recommendation is None else minutes_text(top_recommendation.estimated_wait_minutes),
        "Cost": "n/a" if top_recommendation is None else gbp_text(top_recommendation.estimated_cost_gbp),
        "Grid/risk": risk_indicator_text(option_metadata, response),
        "Status": recommendation_status_text(request, response),
    }


def recommendation_policy_text(response) -> str:
    if response is None:
        return "n/a"

    return str(
        response.metadata.get(
            "effective_policy_name",
            response.metadata.get("requested_policy_name", "n/a"),
        )
    )


def candidate_station_names(response) -> str:
    if response is None:
        return "n/a"

    station_names = []
    if response.top_recommendation is not None:
        station_names.append(response.top_recommendation.station_name)
    station_names.extend(option.station_name for option in response.alternatives)
    return ", ".join(station_names) if station_names else "n/a"


def selected_location_text(request, response) -> str:
    if request is not None:
        selected_name = request.metadata.get("selected_location_name")
        if selected_name:
            return selected_name
        if request.zone_id:
            return request.zone_id
        if request.current_latitude is not None and request.current_longitude is not None:
            return f"{request.current_latitude:.4f}, {request.current_longitude:.4f}"
    if response is not None and response.zone_id:
        return response.zone_id
    return "Unknown"


def charging_need_text(request) -> str:
    if request is None:
        return "n/a"
    if request.requested_energy_kwh is not None:
        return f"{request.requested_energy_kwh:.1f} kWh, {request.preference_mode}"
    if request.current_soc is not None and request.target_soc is not None:
        return f"{request.current_soc:.0f}% to {request.target_soc:.0f}%, {request.preference_mode}"
    return request.preference_mode


def risk_indicator_text(metadata: dict, response) -> str:
    if metadata.get("rl_safety_status"):
        safety_status = str(metadata["rl_safety_status"])
        safety_score = score_text(metadata.get("rl_safety_score"))
        return f"{safety_status} ({safety_score})"
    if response is not None and response.metadata.get("grid_truth_level"):
        return str(response.metadata["grid_truth_level"])
    return "n/a"


def recommendation_status_text(request, response) -> str:
    if request is None:
        return "unmatched response"
    if response is None:
        return "unmatched request"
    if response.top_recommendation is None:
        return "no feasible station"
    option_metadata = response.top_recommendation.metadata
    if option_metadata.get("rl_safety_blocked") is True:
        return "blocked by risk filter"
    if option_metadata.get("fallback_used") is True:
        return "fallback used"
    return "matched"


def recommendation_history_frame(external_requests, recommendations) -> pd.DataFrame:
    rows = recommendation_matches(external_requests, recommendations)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def recommendation_candidate_frame(response) -> pd.DataFrame:
    if response is None:
        return pd.DataFrame()

    options = []
    if response.top_recommendation is not None:
        options.append(("Selected", response.top_recommendation))
    options.extend(("Alternative", option) for option in response.alternatives)
    rows = [candidate_row(rank + 1, label, option) for rank, (label, option) in enumerate(options)]
    return pd.DataFrame(rows)


def recommendation_summary_frame(response) -> pd.DataFrame:
    if response is None or response.top_recommendation is None:
        return pd.DataFrame()

    top_recommendation = response.top_recommendation
    return pd.DataFrame(
        [
            {
                "Station": top_recommendation.station_name,
                "Score": score_text(top_recommendation.score),
                "Wait": minutes_text(top_recommendation.estimated_wait_minutes),
                "Charge time": minutes_text(top_recommendation.estimated_duration_minutes),
                "Cost": recommendation_cost_text(top_recommendation.estimated_cost_gbp),
            }
        ]
    )


def candidate_row(rank: int, label: str, option) -> dict:
    option_metadata = option.metadata
    return {
        "Rank": rank,
        "Type": label,
        "Station": option.station_name,
        "Score": score_text(option.score),
        "Wait": minutes_text(option.estimated_wait_minutes),
        "Cost": gbp_text(option.estimated_cost_gbp),
        "Queue": option.current_queue,
        "Utilization": percentage_text(option.utilization),
        "Headroom": kw_text(option.transformer_headroom_kw),
        "Distance": f"{option.distance_km:.2f} km",
        "Connector": option_metadata.get("selected_connector_type", option_metadata.get("connector_mix_total", "n/a")),
        "Grid/risk": risk_indicator_text(option_metadata, None),
        "Status": candidate_status_text(option_metadata),
    }


def candidate_status_text(option_metadata: dict) -> str:
    if option_metadata.get("rl_safety_blocked") is True:
        return "blocked"
    if option_metadata.get("fallback_used") is True:
        return "fallback"
    if option_metadata.get("routing_fallback_used") is True:
        return "routing fallback"
    if option_metadata.get("tariff_fallback_used") is True:
        return "tariff fallback"
    return "available"


def recommendation_cost_text(amount: float | None) -> str:
    if amount is None:
        return "Cost pending"

    return gbp_text(amount)


def station_filter_options(state, recommendations) -> list[str]:
    station_names = {station.station_name for station in state.stations}
    for response in recommendations:
        if response.top_recommendation is not None:
            station_names.add(response.top_recommendation.station_name)
        station_names.update(option.station_name for option in response.alternatives)
    return ["All stations", *sorted(station_names)]


def status_filter_options(history_frame: pd.DataFrame) -> list[str]:
    if history_frame.empty or "Status" not in history_frame.columns:
        return ["All statuses"]
    return ["All statuses", *sorted(str(status) for status in history_frame["Status"].dropna().unique())]


def policy_filter_options(history_frame: pd.DataFrame) -> list[str]:
    if history_frame.empty or "Policy" not in history_frame.columns:
        return ["All policies"]
    return ["All policies", *sorted(str(policy) for policy in history_frame["Policy"].dropna().unique())]


def filtered_recommendation_history(
    history_frame: pd.DataFrame,
    *,
    station: str,
    policy: str,
    status: str,
    latest_count: int,
) -> pd.DataFrame:
    if history_frame.empty:
        return history_frame

    filtered_frame = history_frame.copy()
    if station != "All stations":
        station_matches = filtered_frame["Candidate stations"].str.contains(station, regex=False, na=False)
        filtered_frame = filtered_frame[station_matches | (filtered_frame["Recommended station"] == station)]
    if policy != "All policies":
        filtered_frame = filtered_frame[filtered_frame["Policy"] == policy]
    if status != "All statuses":
        filtered_frame = filtered_frame[filtered_frame["Status"] == status]
    return filtered_frame.head(latest_count)


def station_map_frame(state) -> pd.DataFrame:
    station_rows = model_rows(state.stations)

    if not station_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(station_rows)
    map_frame = frame.rename(columns={"latitude": "lat", "longitude": "lon"})
    return map_frame.dropna(subset=["lat", "lon"])


def station_map_table_frame(map_frame: pd.DataFrame) -> pd.DataFrame:
    if map_frame.empty:
        return pd.DataFrame()

    visible_columns = [
        "station_name",
        "zone_id",
        "active_sessions",
        "queue_length",
        "utilization",
        "estimated_wait_minutes",
        "transformer_headroom_kw",
    ]
    table_frame = map_frame[[column for column in visible_columns if column in map_frame.columns]].copy()
    table_frame = table_frame.rename(
        columns={
            "station_name": "Station",
            "zone_id": "Zone",
            "active_sessions": "Charging",
            "queue_length": "Queued",
            "utilization": "Utilization",
            "estimated_wait_minutes": "Wait min",
            "transformer_headroom_kw": "Headroom kW",
        }
    )
    return table_frame.sort_values(by=["Queued", "Charging"], ascending=[False, False])


def run_sidebar_controls(runtime: RuntimeManager, status: dict) -> None:
    st.sidebar.header("Demo Controls")

    if st.sidebar.button("Refresh Now"):
        st.rerun()

    refresh_option = st.sidebar.selectbox("Auto-refresh", ["Off", 10, 30, 60], index=0)

    if refresh_option != "Off":
        if st_autorefresh is not None:
            st_autorefresh(
                interval=int(refresh_option) * 1000,
                key="sim_dashboard_autorefresh",
            )
        else:
            st.sidebar.warning("Auto-refresh package is missing. Use Refresh Now.")

    preset = st.sidebar.selectbox("Preset", ["Custom", "Busy Afternoon Demo"])
    use_preset = preset == "Busy Afternoon Demo"
    replay_day = st.sidebar.text_input("Start day", value="2024-06-10")
    start_hour = st.sidebar.selectbox("Start hour", list(range(24)), index=15 if use_preset else 0)
    start_minute = st.sidebar.selectbox("Start minute", [0, 15, 30, 45], index=0)
    policy_mode = st.sidebar.selectbox(
        "Policy",
        ["overload_aware", "cost_aware", "greedy_fastest_service", "random"],
        index=0,
    )
    runtime_mode = st.sidebar.selectbox(
        "Runtime mode",
        ["replay", "synthetic", "hybrid"],
        index=2 if use_preset else 0,
    )
    demand_multiplier = st.sidebar.selectbox(
        "Demand multiplier",
        [0.75, 1.0, 1.25, 1.35, 1.5, 1.75],
        index=3 if use_preset else 1,
    )
    warm_start_hours = st.sidebar.selectbox("Warm-start horizon", [0, 2, 4, 8], index=2 if use_preset else 0)
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

    with st.sidebar.expander("Runtime status JSON"):
        st.json(status)


def render_dashboard_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.75rem;
            color: #0f172a !important;
        }
        div[data-testid="stMetric"] * { color: #0f172a !important; }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetricLabel"] p {
            color: #475569 !important;
        }
        div[data-testid="stMetricValue"] div,
        div[data-testid="stMetricValue"] p {
            color: #0f172a !important;
        }
        .zaproute-map-spacer { margin-bottom: 1.5rem; }
        .stDataFrame { border: 1px solid #e5e7eb; border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_runtime_overview(state, metrics, status_summary: dict) -> None:
    st.subheader("Now")
    runtime_cols = st.columns(4)
    runtime_cols[0].metric("Runtime", status_summary["runtime_status"])
    runtime_cols[1].metric("Loop", "Running" if state.loop_running else "Stopped")
    runtime_cols[2].metric("Simulated time", str(status_summary["simulated_timestamp"]))
    runtime_cols[3].metric("Mode", state.runtime_mode)

    activity_cols = st.columns(5)
    activity_cols[0].metric("Active requests", metrics.active_request_count)
    activity_cols[1].metric("Queued", metrics.queued_request_count)
    activity_cols[2].metric("Charging", metrics.active_session_count)
    activity_cols[3].metric("Completed", metrics.completed_requests_total)
    activity_cols[4].metric(
        "Missed",
        metrics.missed_requests_total,
        delta=metric_delta(metrics.completed_requests_total, metrics.missed_requests_total),
    )

    config_text = (
        f"Policy: {state.active_policy} | Demand x{state.demand_multiplier:.2f} | "
        f"Warm-start: {state.warm_start_minutes} min"
    )
    st.caption(config_text)


def render_attention_summary(metrics) -> None:
    if metrics.overload_event_count > 0:
        st.warning(f"{metrics.overload_event_count} overload events recorded.")
    elif metrics.queued_request_count > 0:
        st.info(f"{metrics.queued_request_count} request(s) are waiting for a charger.")
    elif metrics.active_request_count > 0 or metrics.active_session_count > 0:
        st.success("Runtime is active with no overload events.")
    else:
        st.info("No active requests right now.")


def render_current_activity(state, external_requests, recommendations) -> None:
    st.subheader("Station Activity")
    frame = station_activity_frame(state, external_requests, recommendations)

    if frame.empty:
        st.info("No station activity snapshot available.")
        return

    render_dataframe(frame)
    if has_unassigned_mobile_activity(state, external_requests):
        st.info(
            "Station Activity uses runtime snapshot station assignments from active sessions, queued requests, "
            "active requests, and station snapshots. Mobile reservations or sessions appear here after the "
            "backend/runtime persists their station_id or station_name and active/queued status into those runtime artifacts."
        )


def render_recommendation_history_panel(external_requests, recommendations, state) -> None:
    st.subheader("Recent Recommendation Requests")
    history_frame = recommendation_history_frame(external_requests, recommendations)

    if history_frame.empty:
        st.info("No recommendation requests or responses have been recorded yet.")
        return

    filter_cols = st.columns([0.65, 1.25, 1.0, 1.0])
    latest_count = filter_cols[0].selectbox("Latest", [5, 10, 20], index=1)
    station_name = filter_cols[1].selectbox("Station", station_filter_options(state, recommendations))
    policy_name = filter_cols[2].selectbox("Policy", policy_filter_options(history_frame))
    status_name = filter_cols[3].selectbox("Status", status_filter_options(history_frame))
    visible_frame = filtered_recommendation_history(
        history_frame,
        station=station_name,
        policy=policy_name,
        status=status_name,
        latest_count=int(latest_count),
    )

    if visible_frame.empty:
        st.info("No requests match the selected filters.")
        return

    render_dataframe(visible_frame)


def render_recommendation_panel(recommendations) -> None:
    st.subheader("Matching Recommendation Response")

    if not recommendations:
        st.info("No recommendations have been recorded yet.")
        return

    latest = recommendations[-1]

    if latest.top_recommendation is None:
        st.info("Latest response did not include a top recommendation.")
        return

    top_recommendation = latest.top_recommendation
    summary_frame = recommendation_summary_frame(latest)
    if not summary_frame.empty:
        st.table(summary_frame)

    if top_recommendation.reason_tags:
        st.caption("Why: " + ", ".join(top_recommendation.reason_tags))

    if latest.congestion_note:
        st.info(latest.congestion_note)

    candidate_frame = recommendation_candidate_frame(latest)
    if not candidate_frame.empty:
        render_dataframe(candidate_frame)

    render_recommendation_risk_details(latest)

    with st.expander("Raw latest recommendation"):
        st.json(latest.model_dump(mode="json"))


def render_recommendation_risk_details(response) -> None:
    top_recommendation = response.top_recommendation
    if top_recommendation is None:
        return

    option_metadata = top_recommendation.metadata
    fields = [
        "rl_safety_status",
        "rl_safety_score",
        "rl_safety_penalty",
        "rl_safety_blocked",
        "grid_truth_level",
        "grid_label_source_kind",
        "offline_feeder_rl_adapter",
        "fallback_used",
        "routing_fallback_used",
        "tariff_fallback_used",
    ]
    visible_metadata = {field: option_metadata[field] for field in fields if field in option_metadata}
    if not visible_metadata:
        st.caption("No grid or risk indicators were attached to this response.")
        return

    with st.expander("Grid and risk indicators"):
        st.json(visible_metadata)


def render_station_pressure(state) -> None:
    st.subheader("Station Pressure")
    pressure_frame = station_pressure_frame(state)

    if pressure_frame.empty:
        st.info("No station snapshot available.")
        return

    render_dataframe(pressure_frame)


def render_transformer_pressure(state) -> None:
    st.subheader("Grid Pressure")
    pressure_frame = transformer_pressure_frame(state)

    if pressure_frame.empty:
        st.info("No transformer snapshot available.")
        return

    render_dataframe(pressure_frame)


def render_runtime_configuration(status_summary: dict, status: dict) -> None:
    with st.expander("Runtime Configuration"):
        config_cols = st.columns(4)
        config_cols[0].metric("Recommendation policy", status_summary["recommendation_policy"])
        config_cols[1].metric("Pricing model", status_summary["pricing_model"])
        config_cols[2].metric("Dynamic pricing", "On" if status_summary["dynamic_pricing_enabled"] else "Off")
        config_cols[3].metric("Routing provider", status_summary["routing_provider"])
        st.caption(
            f"Routing available: {status.get('routing_provider_available')} | "
            f"OSMnx graph exists: {status_summary['osmnx_graph_exists']} | "
            f"Last routing fallback: {status.get('last_routing_fallback_reason')}"
        )


def render_optional_details(state, metric_history, events, external_requests) -> None:
    st.subheader("Details")
    show_charts = st.checkbox("Show trend charts", value=False)
    show_events = st.checkbox("Show recent events", value=False)

    if show_charts:
        render_trend_charts(metric_history, events)

    if show_events:
        render_recent_events(events, external_requests)


def render_trend_charts(metric_history, events) -> None:
    history_frame = metric_history_frame(metric_history)

    if history_frame.empty:
        st.info("No metric history yet.")
        return

    chart_columns = [
        "active_request_count",
        "queued_request_count",
        "active_session_count",
        "completed_requests_total",
        "missed_requests_total",
    ]
    visible_columns = [column for column in chart_columns if column in history_frame.columns]
    st.line_chart(history_frame.set_index("simulated_timestamp")[visible_columns])

    arrivals_frame = recent_arrivals_frame(events)
    if not arrivals_frame.empty:
        st.bar_chart(arrivals_frame)


def render_station_map(state) -> None:
    st.subheader("Station Map")
    map_frame = station_map_frame(state)

    if map_frame.empty:
        st.info("No station coordinates available.")
        return

    st.map(map_frame[["lat", "lon"]], height=460, width="stretch")
    st.markdown("<div class='zaproute-map-spacer'></div>", unsafe_allow_html=True)
    missing_coordinate_count = len(state.stations) - len(map_frame)
    if missing_coordinate_count > 0:
        st.warning(f"{missing_coordinate_count} station(s) are missing coordinates and are not shown on the map.")

    table_frame = station_map_table_frame(map_frame)
    if table_frame.empty:
        st.info("No station status rows available.")
        return

    st.markdown("**Mapped Station Details**")
    render_dataframe(table_frame.head(12))


def render_recent_events(events, external_requests) -> None:
    event_frame = recent_events_frame(events)

    if event_frame.empty:
        st.info("No recent runtime events.")
    else:
        render_dataframe(event_frame)

    external_frame = latest_external_frame(external_requests)
    if external_frame.empty:
        return

    st.markdown("**Latest external request**")
    st.json(external_frame.iloc[0].to_dict())


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit is required to run the dashboard UI.")

    st.set_page_config(page_title="ZapRoute Runtime Dashboard", layout="wide")
    render_dashboard_style()
    st.title("ZapRoute Runtime Dashboard")
    st.caption("Live EV-side request, recommendation, station, and grid visibility for the Dundee demo runtime.")

    runtime = RuntimeManager(REPO_ROOT)
    _, state, metrics, metric_history, recommendations, external_requests, events, status = load_runtime_data(REPO_ROOT)
    run_sidebar_controls(runtime, status)

    if state is None or metrics is None:
        st.warning("No runtime snapshot found yet. Use the sidebar to start the Dundee simulator runtime.")
        return

    status_summary = build_status_panel_values(state, metrics, status)
    render_runtime_overview(state, metrics, status_summary)
    render_attention_summary(metrics)
    render_recommendation_history_panel(external_requests, recommendations, state)
    render_station_map(state)

    left_col, right_col = st.columns([1.05, 0.95])

    with left_col:
        render_current_activity(state, external_requests, recommendations)
        render_station_pressure(state)

    with right_col:
        render_recommendation_panel(recommendations)
        render_transformer_pressure(state)

    render_runtime_configuration(status_summary, status)
    render_optional_details(state, metric_history, events, external_requests)


if __name__ == "__main__":
    main()
