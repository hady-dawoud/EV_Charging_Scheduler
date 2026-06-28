"""Streamlit dashboard for the standalone Dundee simulator runtime."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TypeVar

import pandas as pd
from pydantic import BaseModel, ValidationError

try:
    import pydeck as pdk
except ImportError:  # pragma: no cover - exercised when dashboard deps are absent
    pdk = None

try:
    import streamlit as st
except ImportError:  # pragma: no cover - exercised by smoke tests without dashboard deps
    st = None

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.storage import RuntimeStorage  # noqa: E402
from ev_core.contracts.requests import ExternalChargingRequest  # noqa: E402
from ev_core.contracts.responses import RecommendationResponse  # noqa: E402

PydanticRecord = TypeVar("PydanticRecord", bound=BaseModel)
RECENT_REQUEST_LIMIT = 20
RECENT_RESPONSE_LIMIT = 20
RUNTIME_CACHE_TTL_SECONDS = 10
DB_CACHE_TTL_SECONDS = 10
DB_CONNECT_TIMEOUT_SECONDS = 3
DB_STATEMENT_TIMEOUT_MS = 3000
SOURCE_MOBILE_API = "Mobile/API only"
SOURCE_RUNTIME = "Runtime simulation only"
SOURCE_COMBINED = "Combined"
SOURCE_MODE_OPTIONS = [SOURCE_MOBILE_API, SOURCE_RUNTIME, SOURCE_COMBINED]
LOAD_STATE_NORMAL = "Normal"
LOAD_STATE_BUSY = "Busy"
LOAD_STATE_CONGESTED = "Congested"
LOAD_STATE_COLORS = {
    LOAD_STATE_NORMAL: [34, 197, 94, 220],
    LOAD_STATE_BUSY: [234, 179, 8, 230],
    LOAD_STATE_CONGESTED: [239, 68, 68, 235],
}
STATION_MAP_TOOLTIP = {
    "html": (
        "<b>{station_name}</b><br/>"
        "State: {load_state}<br/>"
        "Active: {active_sessions}/{cp_count_total}<br/>"
        "Queued: {queue_length}<br/>"
        "Utilization: {utilization_label}<br/>"
        "Wait: {wait_label}<br/>"
        "Headroom: {headroom_label}"
    ),
    "style": {"backgroundColor": "#111827", "color": "white"},
}


@dataclass(frozen=True)
class MobileActivitySnapshot:
    active_sessions: list[dict]
    open_reservations: list[dict]
    session_status_counts: dict[str, int]
    user_emails_by_id: dict[str, str]
    db_available: bool
    error_message: str | None = None

    @property
    def active_session_count(self) -> int:
        return len(deduplicated_records(self.active_sessions))


def cache_data(ttl_seconds: int):
    def decorator(function):
        if st is None or not hasattr(st, "cache_data") or not streamlit_runtime_available():
            return function
        return st.cache_data(ttl=ttl_seconds, show_spinner=False)(function)

    return decorator


def streamlit_runtime_available() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        return False
    return get_script_run_ctx(suppress_warning=True) is not None


def start_timing(section_name: str) -> float:
    print(f"[dashboard timing] {section_name} start")
    return time.perf_counter()


def finish_timing(section_name: str, section_started_at: float) -> None:
    elapsed_seconds = time.perf_counter() - section_started_at
    print(f"[dashboard timing] {section_name} {elapsed_seconds:.3f}s")


def timed_section(section_name: str, section_call, fallback):
    section_started_at = start_timing(section_name)
    try:
        section_value = section_call()
    except Exception as exc:  # UI boundary: keep the remaining dashboard sections available.
        elapsed_seconds = time.perf_counter() - section_started_at
        print(f"[dashboard timing] {section_name} failed {elapsed_seconds:.3f}s {exc.__class__.__name__}")
        if st is not None:
            st.warning(f"{section_name} failed ({exc.__class__.__name__}). Continuing with the remaining sections.")
        return fallback

    finish_timing(section_name, section_started_at)
    return section_value


def skipped_section(section_name: str) -> None:
    print(f"[dashboard timing] {section_name} skipped 0.000s")


def load_runtime_data(repo_root: Path, *, include_optional: bool = True):
    storage = RuntimeStorage(repo_root)
    state, metrics, status = load_cached_runtime_state(str(repo_root))
    external_requests, recommendations = load_cached_recommendation_artifacts(str(repo_root))
    if include_optional:
        metric_history, events = load_cached_optional_runtime_artifacts(str(repo_root))
    else:
        metric_history, events = [], []
    return storage, state, metrics, metric_history, recommendations, external_requests, events, status


@cache_data(RUNTIME_CACHE_TTL_SECONDS)
def load_cached_runtime_state(repo_root_text: str):
    storage = RuntimeStorage(Path(repo_root_text))
    return storage.load_latest_state(), storage.load_latest_metrics(), storage.load_runtime_status()


@cache_data(RUNTIME_CACHE_TTL_SECONDS)
def load_cached_recommendation_artifacts(repo_root_text: str):
    storage = RuntimeStorage(Path(repo_root_text))
    external_requests = load_recent_external_requests(storage, limit=RECENT_REQUEST_LIMIT)
    recommendations = load_recent_recommendations(storage, limit=RECENT_RESPONSE_LIMIT)
    return external_requests, recommendations


@cache_data(RUNTIME_CACHE_TTL_SECONDS)
def load_cached_optional_runtime_artifacts(repo_root_text: str):
    storage = RuntimeStorage(Path(repo_root_text))
    metric_history = storage.get_metrics_history(limit=24)
    events = storage.get_recent_events(limit=30)
    return metric_history, events


@cache_data(DB_CACHE_TTL_SECONDS)
def load_mobile_activity_snapshot() -> MobileActivitySnapshot:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return MobileActivitySnapshot([], [], {}, {}, db_available=False, error_message="DATABASE_URL is not configured.")

    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError:
        return MobileActivitySnapshot([], [], {}, {}, db_available=False, error_message="SQLAlchemy is not installed.")

    engine = create_engine(database_url, pool_pre_ping=True, connect_args=db_connect_args(database_url))
    try:
        with engine.connect() as connection:
            apply_db_statement_timeout(connection, database_url)
            active_sessions = [dict(row) for row in connection.execute(text(ACTIVE_SESSIONS_SQL)).mappings().all()]
            user_emails_by_id = {
                str(row["user_id"]): str(row["email"])
                for row in active_sessions
                if row.get("user_id") and row.get("email")
            }
    except SQLAlchemyError as exc:
        return MobileActivitySnapshot([], [], {}, {}, db_available=False, error_message=f"Database read failed: {exc.__class__.__name__}.")
    finally:
        engine.dispose()

    session_status_counts = {"active": len(deduplicated_records(active_sessions))}
    return MobileActivitySnapshot(active_sessions, [], session_status_counts, user_emails_by_id, db_available=True)


def db_connect_args(database_url: str) -> dict:
    if database_url.startswith("postgresql"):
        return {"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS}
    return {}


def apply_db_statement_timeout(connection, database_url: str) -> None:
    if not database_url.startswith("postgresql"):
        return
    connection.exec_driver_sql(f"SET statement_timeout = {DB_STATEMENT_TIMEOUT_MS}")


ACTIVE_SESSIONS_SQL = """
SELECT
    CAST(cs.session_id AS TEXT) AS session_id,
    cs.status AS status,
    CAST(cs.user_id AS TEXT) AS user_id,
    u.email AS email,
    cs.station_id AS station_id,
    s.station_name AS station_name,
    CAST(cs.reservation_id AS TEXT) AS reservation_id,
    cs.started_at AS started_at
FROM charging_sessions cs
LEFT JOIN users u ON u.id = cs.user_id
LEFT JOIN stations s ON s.station_id = cs.station_id
WHERE cs.status = 'active'
ORDER BY cs.started_at DESC
"""


def load_recent_external_requests(storage: RuntimeStorage, *, limit: int = RECENT_REQUEST_LIMIT) -> list[ExternalChargingRequest]:
    external_requests = storage.get_recent_external_requests(limit=limit)

    if external_requests:
        return external_requests

    return read_json_records(
        storage.artifacts.latest_external_requests_path,
        ExternalChargingRequest,
        limit=limit,
    )


def load_recent_recommendations(storage: RuntimeStorage, *, limit: int = RECENT_RESPONSE_LIMIT) -> list[RecommendationResponse]:
    recommendations = storage.get_recent_recommendations(limit=limit)

    if recommendations:
        return recommendations

    return read_json_records(
        storage.artifacts.recent_recommendations_path,
        RecommendationResponse,
        limit=limit,
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
        st.dataframe(frame, width="stretch")
    except TypeError:
        try:
            st.dataframe(frame, use_container_width=True)
        except TypeError:
            st.dataframe(frame)


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


def station_activity_frame(
    state,
    external_requests: Iterable[Any] = (),
    recommendations: Iterable[Any] = (),
    mobile_activity: MobileActivitySnapshot | None = None,
    source_mode: str = SOURCE_RUNTIME,
) -> pd.DataFrame:
    activity_by_station = station_activity_by_station(
        state,
        external_requests,
        recommendations,
        mobile_activity,
        source_mode,
    )
    station_rows = [station_activity_row(station, activity_by_station, source_mode) for station in state.stations]

    if not station_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(station_rows)
    return frame.sort_values(
        by=["Queued count", "Active / Charging count", "Utilization ratio"],
        ascending=[False, False, False],
    ).drop(columns=["Utilization ratio"])


def station_activity_row(station, activity_by_station: dict[str, dict], source_mode: str) -> dict:
    station_activity = activity_by_station.get(station.station_id, {})
    active_count = activity_count_or_snapshot(station_activity, station, "active", source_mode)
    queued_count = activity_count_or_snapshot(station_activity, station, "queued", source_mode)
    station_capacity = station_capacity_value(station, station_activity)
    free_slots = station_free_slots(active_count, station_capacity)
    assigned_request_ids = station_request_ids_text(station, station_activity)
    return {
        "Station": station_activity_display_name(station, station_activity, source_mode),
        "Zone": station.zone_id,
        "Source": station_activity_source_text(station_activity, source_mode),
        "Status": effective_station_status(
            station,
            active_count,
            queued_count,
            station_activity,
            station_capacity,
            source_mode,
        ),
        "Active / Charging count": active_count,
        "Queued count": queued_count,
        "Capacity": capacity_text(station_capacity),
        "Free slots": free_slots_text(free_slots),
        "Assigned / active request IDs": assigned_request_ids,
        "Runtime utilization": percentage_text(station.utilization),
        "Utilization ratio": station.utilization,
        "Runtime estimated wait": minutes_text(station.estimated_wait_minutes),
        "Runtime headroom": kw_text(station.transformer_headroom_kw),
    }


def station_activity_by_station(
    state,
    external_requests: Iterable[Any],
    recommendations: Iterable[Any],
    mobile_activity: MobileActivitySnapshot | None,
    source_mode: str,
) -> dict[str, dict]:
    station_lookup = station_identifier_lookup(state.stations)
    activity_by_station: dict[str, dict] = {}

    if source_mode in {SOURCE_MOBILE_API, SOURCE_COMBINED} and mobile_activity is not None:
        add_mobile_active_records(activity_by_station, station_lookup, mobile_activity.active_sessions)
        if source_mode == SOURCE_COMBINED:
            add_mobile_reservation_records(activity_by_station, station_lookup, mobile_activity.open_reservations)

    if source_mode == SOURCE_MOBILE_API:
        return activity_by_station

    if source_mode not in {SOURCE_RUNTIME, SOURCE_COMBINED}:
        return activity_by_station

    add_runtime_active_records(activity_by_station, station_lookup, state.active_sessions)
    add_runtime_active_records(activity_by_station, station_lookup, getattr(state, "charging_requests", []))
    add_runtime_active_records(activity_by_station, station_lookup, getattr(state, "sessions", []))
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


def new_station_activity() -> dict:
    return {
        "mobile_active_ids": [],
        "runtime_active_ids": [],
        "queued_ids": [],
        "assigned_ids": [],
        "capacity": None,
        "station_name": None,
    }


def add_mobile_active_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records) -> None:
    for record in deduplicated_records(records):
        station_id = matched_mobile_session_station_id(record, station_lookup)
        if station_id is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, new_station_activity())
        append_unique(station_activity["mobile_active_ids"], record_request_id(record))
        remember_station_capacity(station_activity, record)
        remember_mobile_station_name(station_activity, record, station_id)


def add_mobile_reservation_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records) -> None:
    for record in records:
        station_id = matched_station_id(record, station_lookup)
        if station_id is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, new_station_activity())
        append_unique(station_activity["assigned_ids"], record_request_id(record))
        remember_station_capacity(station_activity, record)


def add_runtime_active_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records) -> None:
    for record in records:
        station_id = matched_station_id(record, station_lookup)
        if station_id is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, new_station_activity())
        append_unique(station_activity["runtime_active_ids"], record_request_id(record))


def add_station_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records, activity_kind: str) -> None:
    for record in records:
        station_id = matched_station_id(record, station_lookup)
        if station_id is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, new_station_activity())
        record_id = record_request_id(record)
        if activity_kind == "queued":
            append_unique(station_activity["queued_ids"], record_id)
        else:
            append_unique(station_activity["runtime_active_ids"], record_id)


def add_status_records(activity_by_station: dict[str, dict], station_lookup: dict[str, str], records) -> None:
    for record in records:
        station_id = matched_station_id(record, station_lookup)
        activity_kind = record_activity_kind(record)
        if station_id is None or activity_kind is None:
            continue
        station_activity = activity_by_station.setdefault(station_id, new_station_activity())
        if activity_kind == "active":
            append_unique(station_activity["runtime_active_ids"], record_request_id(record))
        else:
            append_unique(station_activity[f"{activity_kind}_ids"], record_request_id(record))


def append_unique(text_values: list[str], text_value: str) -> None:
    if text_value not in text_values:
        text_values.append(text_value)


def deduplicated_records(records) -> list:
    deduplicated = []
    seen_keys = set()
    for record in records:
        identity = activity_record_identity(record)
        if identity in seen_keys:
            continue
        seen_keys.add(identity)
        deduplicated.append(record)
    return deduplicated


def activity_record_identity(record) -> str:
    session_id = first_record_value(record, "session_id")
    if session_id:
        return f"session:{session_id}"

    reservation_id = first_record_value(record, "reservation_id")
    if reservation_id:
        return f"reservation:{reservation_id}"

    request_id = first_record_value(record, "request_id", "client_request_id")
    if request_id:
        return f"request:{request_id}"

    return f"object:{id(record)}"


def remember_station_capacity(station_activity: dict, record) -> None:
    capacity = positive_int_or_none(record_value(record, "station_capacity"))
    if capacity is not None:
        station_activity["capacity"] = capacity


def remember_mobile_station_name(station_activity: dict, record, station_id: str) -> None:
    station_activity["station_name"] = mobile_station_name(record, station_id)


def station_activity_display_name(station, station_activity: dict, source_mode: str) -> str:
    if source_mode in {SOURCE_MOBILE_API, SOURCE_COMBINED} and station_activity.get("mobile_active_ids"):
        return str(station_activity.get("station_name") or station.station_id)
    return station.station_name


def matched_mobile_session_station_id(record, station_lookup: dict[str, str]) -> str | None:
    station_id = record_value(record, "station_id")
    if station_id in station_lookup:
        return station_lookup[station_id]
    return None


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
    request_id = first_record_value(record, "session_id", "request_id", "client_request_id", "reservation_id")
    return str(request_id) if request_id else "unknown"


def activity_count_or_snapshot(station_activity: dict, station, activity_kind: str, source_mode: str) -> int:
    if activity_kind == "queued":
        if source_mode == SOURCE_MOBILE_API:
            return 0
        activity_ids = station_activity.get("queued_ids", [])
        if activity_ids:
            return len(activity_ids)
        return station.queue_length

    mobile_active_ids = station_activity.get("mobile_active_ids", [])
    if source_mode == SOURCE_MOBILE_API:
        return len(mobile_active_ids)

    if mobile_active_ids:
        if source_mode == SOURCE_COMBINED:
            return len(set([*mobile_active_ids, *station_activity.get("runtime_active_ids", [])]))
        return len(mobile_active_ids)

    runtime_active_ids = station_activity.get("runtime_active_ids", [])
    if runtime_active_ids:
        return len(runtime_active_ids)

    return station.active_sessions


def station_request_ids_text(station, station_activity: dict) -> str:
    request_ids = [
        *station_activity.get("mobile_active_ids", []),
        *station_activity.get("runtime_active_ids", []),
        *station_activity.get("queued_ids", []),
        *station_activity.get("assigned_ids", []),
    ]

    if not request_ids:
        request_ids = [*station.active_request_ids, *station.queued_request_ids]

    if not request_ids:
        return "—"

    return ", ".join(short_identifier(request_id) for request_id in request_ids)


def station_activity_source_text(station_activity: dict, source_mode: str) -> str:
    has_mobile = bool(station_activity.get("mobile_active_ids") or station_activity.get("assigned_ids"))
    has_runtime = bool(station_activity.get("runtime_active_ids") or station_activity.get("queued_ids"))

    if source_mode == SOURCE_COMBINED:
        if has_mobile and has_runtime:
            return "Mobile/API + runtime"
        if has_mobile:
            return "Mobile/API"
        if has_runtime:
            return "Runtime simulation"
        return "None"
    if source_mode == SOURCE_MOBILE_API:
        return "Mobile/API"
    if source_mode == SOURCE_RUNTIME:
        return "Runtime simulation"
    return source_mode


def station_status_text(station, active_count: int, queued_count: int, station_activity: dict, station_capacity: int | None) -> str:
    if getattr(station, "blocked", False):
        return "Blocked"
    if getattr(station, "offline", False):
        return "Offline"
    if getattr(station, "available", True) is False:
        return "Unavailable"
    if station_capacity is not None and active_count >= station_capacity:
        return "Full"
    if active_count > 0:
        return "Charging"
    if queued_count > 0:
        return "Queued"
    if station_activity.get("assigned_ids"):
        return "Active"
    return "Available"


def effective_station_status(
    station,
    active_count: int,
    queued_count: int,
    station_activity: dict,
    station_capacity: int | None,
    source_mode: str,
) -> str:
    if source_mode == SOURCE_MOBILE_API and active_count == 0:
        return "Available"

    return station_status_text(station, active_count, queued_count, station_activity, station_capacity)


def station_capacity_value(station, station_activity: dict) -> int | None:
    activity_capacity = positive_int_or_none(station_activity.get("capacity"))
    if activity_capacity is not None:
        return activity_capacity

    return positive_int_or_none(getattr(station, "cp_count_total", None))


def station_free_slots(active_count: int, station_capacity: int | None) -> int | None:
    if station_capacity is None:
        return None

    return max(station_capacity - active_count, 0)


def positive_int_or_none(raw_value) -> int | None:
    if raw_value is None:
        return None

    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        return None

    if parsed_value <= 0:
        return None

    return parsed_value


def capacity_text(station_capacity: int | None) -> str:
    if station_capacity is None:
        return "Unknown"

    return str(station_capacity)


def free_slots_text(free_slots: int | None) -> str:
    if free_slots is None:
        return "Unknown"

    return str(free_slots)


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


def recommendation_matches(external_requests, recommendations, user_emails_by_id: dict[str, str] | None = None) -> list[dict]:
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
        rows.append(recommendation_match_row(request, response, user_emails_by_id or {}))

    for request in reversed(external_requests):
        if id(request) not in matched_request_ids:
            rows.append(recommendation_match_row(request, None, user_emails_by_id or {}))

    return rows


def recommendation_match_row(request, response, user_emails_by_id: dict[str, str]) -> dict:
    top_recommendation = None if response is None else response.top_recommendation
    option_metadata = {} if top_recommendation is None else top_recommendation.metadata
    request_metadata = {} if request is None else request.metadata
    candidate_count = 0 if response is None else len(response.alternatives) + (1 if top_recommendation else 0)
    return {
        "Request time": None if request is None else request.request_timestamp,
        "User": request_user_text(request_metadata, user_emails_by_id),
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


def request_user_text(request_metadata: dict, user_emails_by_id: dict[str, str]) -> str:
    metadata_email = request_metadata.get("user_email") or request_metadata.get("email")
    if metadata_email:
        return str(metadata_email)

    user_id = request_metadata.get("user_id")
    if user_id is None:
        return "n/a"

    return user_emails_by_id.get(str(user_id), str(user_id))


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


def recommendation_history_frame(
    external_requests,
    recommendations,
    user_emails_by_id: dict[str, str] | None = None,
) -> pd.DataFrame:
    rows = recommendation_matches(external_requests, recommendations, user_emails_by_id)

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


def session_status_frame(mobile_activity: MobileActivitySnapshot, metrics) -> pd.DataFrame:
    if mobile_activity.db_available:
        rows = [
            {"Status": status_name, "Sessions": session_count}
            for status_name, session_count in mobile_activity.session_status_counts.items()
        ]
        return pd.DataFrame(rows)

    return pd.DataFrame(
        [
            {"Status": "runtime charging", "Sessions": metrics.active_session_count},
            {"Status": "runtime queued", "Sessions": metrics.queued_request_count},
        ]
    )


def busiest_station_frame(station_activity: pd.DataFrame) -> pd.DataFrame:
    if station_activity.empty:
        return pd.DataFrame()

    chart_frame = station_activity[["Station", "Active / Charging count", "Queued count"]].copy()
    chart_frame["Total"] = chart_frame["Active / Charging count"] + chart_frame["Queued count"]
    return chart_frame.sort_values("Total", ascending=False).head(8).set_index("Station")[["Active / Charging count", "Queued count"]]


def recommendation_station_chart_frame(history_frame: pd.DataFrame) -> pd.DataFrame:
    if history_frame.empty or "Recommended station" not in history_frame.columns:
        return pd.DataFrame()

    chart_frame = history_frame[history_frame["Recommended station"] != "Unmatched"]
    if chart_frame.empty:
        return pd.DataFrame()

    return chart_frame["Recommended station"].value_counts().head(8).rename_axis("Station").reset_index(name="Recommendations")


def candidate_comparison_frame(response) -> pd.DataFrame:
    if response is None:
        return pd.DataFrame()

    options = []
    if response.top_recommendation is not None:
        options.append(response.top_recommendation)
    options.extend(response.alternatives)

    return pd.DataFrame(
        [
            {
                "Station": option.station_name,
                "Score": option.score,
                "Cost": option.estimated_cost_gbp,
                "Wait": option.estimated_wait_minutes,
            }
            for option in options[:6]
        ]
    )


def active_mobile_sessions_by_station_frame(mobile_activity: MobileActivitySnapshot) -> pd.DataFrame:
    records = deduplicated_records(mobile_activity.active_sessions)
    if not records:
        return pd.DataFrame()

    rows = []
    for station_id, station_records in grouped_records_by_station(records).items():
        first_record = station_records[0]
        rows.append(
            {
                "Station": mobile_station_name(first_record, station_id),
                "Station ID": station_id,
                "Active sessions": len(station_records),
                "Capacity": capacity_text(positive_int_or_none(record_value(first_record, "station_capacity"))),
                "Session IDs": ", ".join(short_identifier(record_request_id(record)) for record in station_records),
                "Users": ", ".join(session_user_text(record) for record in station_records),
            }
        )

    return pd.DataFrame(rows).sort_values(["Active sessions", "Station"], ascending=[False, True])


def grouped_records_by_station(records) -> dict[str, list]:
    grouped_records: dict[str, list] = {}
    for record in records:
        station_id = str(record_value(record, "station_id") or "unknown")
        grouped_records.setdefault(station_id, []).append(record)
    return grouped_records


def mobile_station_name(record, station_id: str) -> str:
    station_name = record_value(record, "station_name")
    if station_name:
        return str(station_name)
    return station_id


def session_user_text(record) -> str:
    user_email = first_record_value(record, "email", "user_email")
    if user_email:
        return str(user_email)

    user_id = record_value(record, "user_id")
    if user_id:
        return short_identifier(str(user_id))

    return "n/a"


def raw_active_session_rows_frame(mobile_activity: MobileActivitySnapshot) -> pd.DataFrame:
    records = deduplicated_records(mobile_activity.active_sessions)
    if not records:
        return pd.DataFrame()

    rows = [
        {
            "session_id": record_value(record, "session_id"),
            "email": first_record_value(record, "email", "user_email") or "n/a",
            "station_id": record_value(record, "station_id") or "n/a",
            "station_name": mobile_station_name(record, str(record_value(record, "station_id") or "n/a")),
            "reservation_id": record_value(record, "reservation_id") or "n/a",
            "started_at": record_value(record, "started_at") or "n/a",
        }
        for record in records
    ]
    return pd.DataFrame(rows)


def station_map_frame(state) -> pd.DataFrame:
    station_rows = [station_map_row(station) for station in state.stations]

    if not station_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(station_rows)
    map_frame = frame.rename(columns={"latitude": "lat", "longitude": "lon"})
    return map_frame.dropna(subset=["lat", "lon"])


def station_map_row(station) -> dict:
    station_row = station.model_dump(mode="json")
    load_state = station_load_state(station)
    station_row["load_state"] = load_state
    station_row["map_color"] = LOAD_STATE_COLORS[load_state]
    station_row["utilization_label"] = percentage_text(station.utilization)
    station_row["wait_label"] = minutes_text(station.estimated_wait_minutes)
    station_row["headroom_label"] = kw_text(station.transformer_headroom_kw)
    return station_row


def station_load_state(station) -> str:
    if station.queue_length > 0 or station.utilization >= 0.8 or station.transformer_headroom_kw <= 0:
        return LOAD_STATE_CONGESTED

    if (
        station.active_sessions > 0
        or station.utilization >= 0.4
        or station.estimated_wait_minutes > 0
        or station.transformer_headroom_kw < station.station_capacity_kw_assumed
    ):
        return LOAD_STATE_BUSY

    return LOAD_STATE_NORMAL


def station_map_table_frame(map_frame: pd.DataFrame) -> pd.DataFrame:
    if map_frame.empty:
        return pd.DataFrame()

    visible_columns = [
        "station_name",
        "load_state",
        "zone_id",
        "cp_count_total",
        "lat",
        "lon",
        "utilization",
        "transformer_headroom_kw",
    ]
    table_frame = map_frame[[column for column in visible_columns if column in map_frame.columns]].copy()
    table_frame = table_frame.rename(
        columns={
            "station_name": "Station",
            "load_state": "Load state",
            "zone_id": "Zone",
            "cp_count_total": "Capacity",
            "lat": "Latitude",
            "lon": "Longitude",
            "utilization": "Runtime utilization",
            "transformer_headroom_kw": "Runtime headroom kW",
        }
    )
    return table_frame.sort_values(by=["Station"])


def station_map_frames(state) -> tuple[pd.DataFrame, pd.DataFrame]:
    map_frame = station_map_frame(state)
    return map_frame, station_map_table_frame(map_frame)


def station_map_deck(map_frame: pd.DataFrame):
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_frame,
        get_position="[lon, lat]",
        get_fill_color="map_color",
        get_radius=90,
        radius_min_pixels=8,
        radius_max_pixels=18,
        pickable=True,
        auto_highlight=True,
    )
    return pdk.Deck(
        map_style="light",
        initial_view_state=station_map_view_state(map_frame),
        layers=[scatter_layer],
        tooltip=STATION_MAP_TOOLTIP,
    )


def station_map_view_state(map_frame: pd.DataFrame):
    return pdk.ViewState(
        latitude=float(map_frame["lat"].mean()),
        longitude=float(map_frame["lon"].mean()),
        zoom=11,
        min_zoom=9,
        max_zoom=16,
    )


def new_runtime_manager():
    from services.sim_runtime.runtime_manager import RuntimeManager

    return RuntimeManager(REPO_ROOT)


def run_sidebar_controls(status: dict) -> None:
    st.sidebar.header("Demo Controls")

    if st.sidebar.button("Refresh Now"):
        st.rerun()

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
        runtime = new_runtime_manager()
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
        runtime = new_runtime_manager()
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
        runtime = new_runtime_manager()
        runtime.stop_loop()
        st.sidebar.info("Loop stop requested.")

    if st.sidebar.button("Tick Once"):
        runtime = new_runtime_manager()
        runtime.tick(steps=1)
        st.sidebar.success("Advanced one 15-minute simulation slot.")

    if st.sidebar.button("Busy Afternoon Demo"):
        runtime = new_runtime_manager()
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


def render_page_header() -> None:
    header_cols = st.columns([0.82, 0.18])
    with header_cols[0]:
        st.title("ZapRoute Runtime Dashboard")
        st.caption("Live EV-side request, recommendation, station, and grid visibility for the Dundee demo runtime.")
    with header_cols[1]:
        st.write("")
        if st.button("Refresh", use_container_width=True):
            st.rerun()


def effective_charging_count(metrics, mobile_activity: MobileActivitySnapshot) -> int:
    if mobile_activity.db_available:
        return mobile_activity.active_session_count

    return metrics.active_session_count


def effective_active_request_count(metrics, mobile_activity: MobileActivitySnapshot) -> int:
    if not mobile_activity.db_available:
        return metrics.active_request_count

    return mobile_activity.active_session_count + unlinked_open_reservation_count(mobile_activity)


def unlinked_open_reservation_count(mobile_activity: MobileActivitySnapshot) -> int:
    active_reservation_ids = {
        str(reservation_id)
        for reservation_id in (
            first_record_value(record, "reservation_id")
            for record in deduplicated_records(mobile_activity.active_sessions)
        )
        if reservation_id
    }
    open_reservation_ids = {
        str(reservation_id)
        for reservation_id in (
            first_record_value(record, "reservation_id")
            for record in mobile_activity.open_reservations
        )
        if reservation_id and str(reservation_id) not in active_reservation_ids
    }
    return len(open_reservation_ids)


def render_runtime_overview(state, metrics, status_summary: dict, mobile_activity: MobileActivitySnapshot) -> None:
    st.subheader("Now")
    runtime_cols = st.columns(4)
    runtime_cols[0].metric("Runtime", status_summary["runtime_status"])
    runtime_cols[1].metric("Loop", "Running" if state.loop_running else "Stopped")
    runtime_cols[2].metric("Simulated time", str(status_summary["simulated_timestamp"]))
    runtime_cols[3].metric("Mode", state.runtime_mode)

    activity_cols = st.columns(5)
    activity_cols[0].metric("Active requests", effective_active_request_count(metrics, mobile_activity))
    activity_cols[1].metric("Queued", metrics.queued_request_count)
    activity_cols[2].metric("Charging", effective_charging_count(metrics, mobile_activity))
    activity_cols[3].metric("Completed", metrics.completed_requests_total)
    activity_cols[4].metric("Missed", metrics.missed_requests_total)

    config_text = (
        f"Policy: {state.active_policy} | Demand x{state.demand_multiplier:.2f} | "
        f"Warm-start: {state.warm_start_minutes} min"
    )
    st.caption(config_text)
    render_mobile_activity_notice(mobile_activity)


def render_mobile_activity_notice(mobile_activity: MobileActivitySnapshot) -> None:
    if mobile_activity.db_available:
        st.caption("Charging count and Station Activity use active API/mobile sessions from PostgreSQL.")
        return

    st.info(
        "API/mobile session DB data is unavailable. Now metrics fall back to runtime counters; "
        f"Station Activity stays separated by the selected source. Detail: {mobile_activity.error_message}"
    )


def render_attention_summary(metrics, mobile_activity: MobileActivitySnapshot) -> None:
    if metrics.overload_event_count > 0:
        st.warning(f"{metrics.overload_event_count} overload events recorded.")
    elif metrics.queued_request_count > 0:
        st.info(f"{metrics.queued_request_count} request(s) are waiting for a charger.")
    elif effective_active_request_count(metrics, mobile_activity) > 0 or effective_charging_count(metrics, mobile_activity) > 0:
        st.success("Runtime is active with no overload events.")
    else:
        st.info("No active requests right now.")


def render_current_activity(state, external_requests, recommendations, mobile_activity: MobileActivitySnapshot) -> None:
    st.subheader("Station Activity")
    source_mode = st.radio(
        "Station activity source",
        SOURCE_MODE_OPTIONS,
        index=0,
        horizontal=True,
    )
    st.caption(
        "Mobile/API only reflects actual app reservations and charging sessions from Postgres. "
        "Runtime simulation only reflects simulated runtime state."
    )
    frame = timed_section(
        "station activity build",
        lambda: station_activity_frame(
            state,
            external_requests,
            recommendations,
            mobile_activity,
            source_mode=source_mode,
        ),
        pd.DataFrame(),
    )

    if frame.empty:
        st.info("No station activity snapshot available.")
        return

    render_dataframe(frame)
    render_active_mobile_sessions_guard(mobile_activity)
    if has_unassigned_mobile_activity(state, external_requests):
        st.info(
            "Station Activity uses runtime snapshot station assignments from active sessions, queued requests, "
            "active requests, and station snapshots. Mobile reservations or sessions appear here after the "
            "backend/runtime persists their station_id or station_name and active/queued status into those runtime artifacts."
        )


def render_active_mobile_sessions_guard(mobile_activity: MobileActivitySnapshot) -> None:
    if not mobile_activity.db_available:
        return

    session_frame = active_mobile_sessions_by_station_frame(mobile_activity)
    if session_frame.empty:
        st.info("No active Postgres charging_sessions rows were found.")
        return

    st.markdown("**Active Mobile/API Sessions by Station**")
    st.caption(
        f"Active Postgres charging_sessions total: {mobile_activity.active_session_count}. "
        "Use this table to spot stale active sessions by station, user, and session ID."
    )
    render_dataframe(session_frame)

    raw_session_frame = raw_active_session_rows_frame(mobile_activity)
    if not raw_session_frame.empty:
        with st.expander("Raw Active Mobile/API Session Rows"):
            render_dataframe(raw_session_frame)


def render_activity_charts(
    station_activity: pd.DataFrame,
    history_frame: pd.DataFrame,
    latest_recommendation,
    mobile_activity: MobileActivitySnapshot,
    metrics,
) -> None:
    st.subheader("Quick Charts")
    left_col, right_col = st.columns(2)

    with left_col:
        render_session_status_chart(mobile_activity, metrics)
        render_recommendation_station_chart(history_frame)

    with right_col:
        render_busiest_station_chart(station_activity)
        render_candidate_comparison_chart(latest_recommendation)


def render_session_status_chart(mobile_activity: MobileActivitySnapshot, metrics) -> None:
    status_frame = session_status_frame(mobile_activity, metrics)
    if status_frame.empty:
        st.info("No session status data available.")
        return

    st.markdown("**Sessions by Status**")
    st.vega_lite_chart(
        status_frame,
        {
            "mark": {"type": "arc", "innerRadius": 35},
            "encoding": {
                "theta": {"field": "Sessions", "type": "quantitative"},
                "color": {"field": "Status", "type": "nominal"},
                "tooltip": ["Status", "Sessions"],
            },
        },
        use_container_width=True,
    )


def render_busiest_station_chart(station_activity: pd.DataFrame) -> None:
    chart_frame = busiest_station_frame(station_activity)
    if chart_frame.empty:
        st.info("No station activity data available.")
        return

    st.markdown("**Busiest Stations**")
    st.bar_chart(chart_frame)


def render_recommendation_station_chart(history_frame: pd.DataFrame) -> None:
    chart_frame = recommendation_station_chart_frame(history_frame)
    if chart_frame.empty:
        st.info("No recommendation station history available.")
        return

    st.markdown("**Recommendations by Station**")
    st.bar_chart(chart_frame.set_index("Station"))


def render_candidate_comparison_chart(latest_recommendation) -> None:
    chart_frame = candidate_comparison_frame(latest_recommendation)
    if chart_frame.empty:
        st.info("No candidate comparison data available.")
        return

    st.markdown("**Candidate Score / Cost / Wait**")
    st.bar_chart(chart_frame.set_index("Station"))


def render_recommendation_history_panel(external_requests, recommendations, state, mobile_activity: MobileActivitySnapshot) -> None:
    st.subheader("Recent Recommendation Requests")
    history_frame = recommendation_history_frame(
        external_requests,
        recommendations,
        mobile_activity.user_emails_by_id,
    )

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


def render_optional_details(state, external_requests) -> None:
    st.subheader("Details")
    show_charts = st.checkbox("Show trend charts", value=False)
    show_events = st.checkbox("Show recent events", value=False)

    if not show_charts and not show_events:
        return

    metric_history, events = timed_section(
        "runtime optional artifacts load",
        lambda: load_cached_optional_runtime_artifacts(str(REPO_ROOT)),
        ([], []),
    )

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


def render_station_map(state, map_frame: pd.DataFrame, table_frame: pd.DataFrame, show_map: bool) -> None:
    st.subheader("Station Map")

    if map_frame.empty:
        st.info("No station coordinates available.")
        return

    if show_map:
        if pdk is None:
            st.map(map_frame[["lat", "lon"]], height=460, width="stretch")
        else:
            st.pydeck_chart(station_map_deck(map_frame), height=460, width="stretch")
    else:
        st.caption("Map rendering is disabled for faster initial load. Enable Show map to draw station coordinates.")

    st.markdown("<div class='zaproute-map-spacer'></div>", unsafe_allow_html=True)
    missing_coordinate_count = len(state.stations) - len(map_frame)
    if missing_coordinate_count > 0:
        st.warning(f"{missing_coordinate_count} station(s) are missing coordinates and are not shown on the map.")

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

    dashboard_started_at = start_timing("dashboard start")
    st.set_page_config(page_title="ZapRoute Runtime Dashboard", layout="wide")
    render_dashboard_style()
    render_page_header()

    state, metrics, status = timed_section(
        "runtime/state load",
        lambda: load_cached_runtime_state(str(REPO_ROOT)),
        (None, None, {}),
    )
    external_requests, recommendations = timed_section(
        "recommendations/request artifacts load",
        lambda: load_cached_recommendation_artifacts(str(REPO_ROOT)),
        ([], []),
    )
    mobile_activity = timed_section(
        "DB active sessions load",
        load_mobile_activity_snapshot,
        MobileActivitySnapshot([], [], {}, {}, db_available=False, error_message="DB load failed."),
    )
    run_sidebar_controls(status)

    if state is None or metrics is None:
        st.warning("No runtime snapshot found yet. Use the sidebar to start the Dundee simulator runtime.")
        finish_timing("render complete", dashboard_started_at)
        return

    status_summary = build_status_panel_values(state, metrics, status)
    history_frame = recommendation_history_frame(external_requests, recommendations, mobile_activity.user_emails_by_id)
    latest_recommendation = recommendations[-1] if recommendations else None
    map_frame, map_table_frame = timed_section(
        "mapped station details build",
        lambda: station_map_frames(state),
        (pd.DataFrame(), pd.DataFrame()),
    )

    render_runtime_overview(state, metrics, status_summary, mobile_activity)
    render_attention_summary(metrics, mobile_activity)
    render_recommendation_history_panel(external_requests, recommendations, state, mobile_activity)

    show_charts = st.checkbox("Show charts", value=False)
    if show_charts:
        timed_section(
            "charts build",
            lambda: render_activity_charts(
                station_activity_frame(
                    state,
                    external_requests,
                    recommendations,
                    mobile_activity,
                    source_mode=SOURCE_MOBILE_API,
                ),
                history_frame,
                latest_recommendation,
                mobile_activity,
                metrics,
            ),
            None,
        )
    else:
        skipped_section("charts build")

    show_map = st.checkbox("Show map", value=False)
    timed_section(
        "map build",
        lambda: render_station_map(state, map_frame, map_table_frame, show_map),
        None,
    )

    left_col, right_col = st.columns([1.05, 0.95])

    with left_col:
        render_current_activity(state, external_requests, recommendations, mobile_activity)
        render_station_pressure(state)

    with right_col:
        render_recommendation_panel(recommendations)
        render_transformer_pressure(state)

    render_runtime_configuration(status_summary, status)
    render_optional_details(state, external_requests)
    finish_timing("render complete", dashboard_started_at)


if __name__ == "__main__":
    main()
