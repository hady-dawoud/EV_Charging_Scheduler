from __future__ import annotations

import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest


try:
    _np = importlib.import_module("numpy")
    if not hasattr(_np, "__version__"):
        sys.modules.pop("numpy", None)
    _pd = importlib.import_module("pandas")
    if not hasattr(_pd, "read_csv"):
        sys.modules.pop("pandas", None)
        _pd = importlib.import_module("pandas")
except ModuleNotFoundError:
    _pd = None

if _pd is not None and hasattr(_pd, "read_csv"):
    sys.modules.pop("ev_core.data.repositories", None)
    sys.modules.pop("ev_core.forecasting.provider", None)
    sys.modules.pop("services.sim_runtime.runtime_manager", None)

pytestmark = pytest.mark.skipif(
    _pd is None or not hasattr(_pd, "read_csv"),
    reason="dashboard smoke tests require real pandas",
)

from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import (
    MetricsSnapshot,
    RecommendationOption,
    RecommendationResponse,
    RequestSnapshot,
    StateSnapshot,
    StationStateSnapshot,
)


def test_dashboard_imports_and_loads_fresh_runtime_state() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    repo_root = Path(__file__).resolve().parents[2]
    storage_root = repo_root / "outputs" / "test_runtime" / f"dashboard_{uuid4().hex}"
    manager = RuntimeManager(repo_root)
    manager.storage = RuntimeStorage(storage_root)
    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)

    _, state, metrics, metric_history, recommendations, external_requests, events, status = dashboard_app.load_runtime_data(storage_root)
    summary = dashboard_app.build_status_panel_values(state, metrics, status)

    assert state is not None
    assert metrics is not None
    assert metric_history
    assert recommendations == []
    assert external_requests == []
    assert events
    assert summary["runtime_status"] == "running"
    assert summary["simulated_timestamp"] == state.simulated_timestamp
    assert summary["recommendation_policy"] == "weighted_score"
    assert summary["pricing_model"] == "dundee_tariff_plus_dynamic_overlay"
    assert summary["dynamic_pricing_enabled"] is True
    assert summary["routing_provider"] == "simple_distance"
    assert isinstance(summary["osmnx_graph_exists"], bool)


def test_dashboard_uses_typed_json_request_response_fallback() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    repo_root = Path(__file__).resolve().parents[2]
    storage_root = repo_root / "outputs" / "test_runtime" / f"dashboard_fallback_{uuid4().hex}"
    storage = RuntimeStorage(storage_root)
    request_time = datetime.fromisoformat("2024-06-10T15:00:00")
    external_request = ExternalChargingRequest(
        client_request_id="mobile-demo-request",
        request_timestamp=request_time,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=24.0,
        preference_mode="fastest",
        charger_type="Any",
        latest_finish_ts=request_time + timedelta(minutes=90),
        metadata={
            "selected_location_name": "Central Dundee",
            "user_id": "demo-user",
        },
    )
    recommendation = RecommendationResponse(
        request_id="external-demo-runtime",
        client_request_id="mobile-demo-request",
        simulated_timestamp=request_time,
        zone_id="zone_central_waterfront",
        top_recommendation=RecommendationOption(
            station_id="greenmarket_150kw_bus_charger",
            station_name="Greenmarket 150kW Bus Charger",
            zone_id="zone_central_waterfront",
            transformer_id="tx_central_market",
            score=0.91,
            distance_km=0.5,
            estimated_wait_minutes=0,
            estimated_duration_minutes=15,
            estimated_cost_gbp=18.4,
            transformer_headroom_kw=220.0,
            current_queue=0,
            utilization=0.5,
            charger_compatible=True,
            reason_tags=["low_wait"],
            metadata={
                "rl_safety_status": "safe",
                "rl_safety_score": 0.88,
                "grid_truth_level": "area_pf",
            },
        ),
        metadata={"effective_policy_name": "rl_safety_preference"},
    )
    storage.artifacts.latest_external_requests_path.write_text(
        external_request.model_dump_json(indent=2).join(["[\n", "\n]\n"]),
        encoding="utf-8",
    )
    storage.artifacts.recent_recommendations_path.write_text(
        recommendation.model_dump_json(indent=2).join(["[\n", "\n]\n"]),
        encoding="utf-8",
    )

    _, _, _, _, recommendations, external_requests, _, _ = dashboard_app.load_runtime_data(storage_root)
    history_frame = dashboard_app.recommendation_history_frame(
        external_requests,
        recommendations,
        {"demo-user": "demo.user@example.edu"},
    )
    candidate_frame = dashboard_app.recommendation_candidate_frame(recommendations[0])

    assert len(external_requests) == 1
    assert len(recommendations) == 1
    assert history_frame.iloc[0]["Status"] == "matched"
    assert history_frame.iloc[0]["User"] == "demo.user@example.edu"
    assert history_frame.iloc[0]["Location"] == "Central Dundee"
    assert history_frame.iloc[0]["Grid/risk"] == "safe (0.880)"
    assert candidate_frame.iloc[0]["Station"] == "Greenmarket 150kW Bus Charger"


def test_station_activity_uses_session_and_queue_records_before_station_counts() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("camperdown_country_park", "Camperdown Country Park"),
            _station_snapshot("lochee_charging_hub_aimer_square_dundee", "Lochee Charging Hub, Aimer Square, Dundee"),
        ],
        active_sessions=[
            _request_snapshot(
                request_id="camp-session-01",
                status="charging",
                station_id="camperdown_country_park",
                station_name="Camperdown Country Park",
            )
        ],
        queued_requests=[
            _request_snapshot(
                request_id="lochee-queue-01",
                status="queued",
                station_id="lochee_charging_hub_aimer_square_dundee",
                station_name="Lochee Charging Hub, Aimer Square, Dundee",
            )
        ],
    )

    frame = dashboard_app.station_activity_frame(state)
    camperdown = frame[frame["Station"] == "Camperdown Country Park"].iloc[0]
    lochee = frame[frame["Station"] == "Lochee Charging Hub, Aimer Square, Dundee"].iloc[0]

    assert camperdown["Status"] == "Charging"
    assert camperdown["Active / Charging count"] == 1
    assert camperdown["Assigned / active request IDs"] == "camp-session-01"
    assert lochee["Status"] == "Queued"
    assert lochee["Queued count"] == 1
    assert lochee["Assigned / active request IDs"] == "lochee-queue-01"


def test_station_activity_uses_persisted_station_status_artifacts() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("camperdown_country_park", "Camperdown Country Park"),
        ],
    )
    artifact_record = {
        "request_id": "camp-artifact-01",
        "status": "active",
        "selected_station_id": "camperdown_country_park",
    }

    frame = dashboard_app.station_activity_frame(state, external_requests=[artifact_record])
    camperdown = frame[frame["Station"] == "Camperdown Country Park"].iloc[0]

    assert camperdown["Status"] == "Charging"
    assert camperdown["Active / Charging count"] == 1
    assert camperdown["Assigned / active request IDs"] == "camp-artifact-01"


def test_station_activity_prefers_mobile_sessions_for_capacity_and_status() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("camperdown_country_park", "Camperdown Country Park"),
        ],
    )
    mobile_activity = dashboard_app.MobileActivitySnapshot(
        active_sessions=[
            {
                "session_id": f"camp-0{index}",
                "status": "active",
                "station_id": "camperdown_country_park",
                "station_name": "Camperdown Country Park",
                "station_capacity": 5,
            }
            for index in range(5)
        ],
        open_reservations=[],
        session_status_counts={"active": 5},
        user_emails_by_id={},
        db_available=True,
    )

    frame = dashboard_app.station_activity_frame(
        state,
        mobile_activity=mobile_activity,
        source_mode=dashboard_app.SOURCE_MOBILE_API,
    )
    camperdown = frame[frame["Station"] == "Camperdown Country Park"].iloc[0]

    assert camperdown["Status"] == "Full"
    assert camperdown["Active / Charging count"] == 5
    assert camperdown["Capacity"] == "5"
    assert camperdown["Free slots"] == "0"
    assert dashboard_app.effective_charging_count(state.metrics, mobile_activity) == 5


def test_mobile_active_sessions_are_counted_once() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("camperdown_country_park", "Camperdown Country Park"),
        ],
    )
    mobile_activity = dashboard_app.MobileActivitySnapshot(
        active_sessions=[
            _mobile_session("session-01", "camperdown_country_park", "Camperdown Country Park", station_capacity=5),
            _mobile_session("session-01", "camperdown_country_park", "Camperdown Country Park", station_capacity=5),
        ],
        open_reservations=[],
        session_status_counts={"active": 2},
        user_emails_by_id={},
        db_available=True,
    )

    frame = dashboard_app.station_activity_frame(
        state,
        mobile_activity=mobile_activity,
        source_mode=dashboard_app.SOURCE_MOBILE_API,
    )
    camperdown = frame[frame["Station"] == "Camperdown Country Park"].iloc[0]

    assert dashboard_app.effective_charging_count(state.metrics, mobile_activity) == 1
    assert camperdown["Active / Charging count"] == 1


def test_mobile_only_station_activity_ignores_runtime_sessions() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("camperdown_country_park", "Camperdown Country Park"),
        ],
        active_sessions=[
            _request_snapshot(
                request_id="runtime-session-01",
                status="charging",
                station_id="camperdown_country_park",
                station_name="Camperdown Country Park",
            )
        ],
    )
    mobile_activity = dashboard_app.MobileActivitySnapshot(
        active_sessions=[],
        open_reservations=[],
        session_status_counts={},
        user_emails_by_id={},
        db_available=True,
    )

    frame = dashboard_app.station_activity_frame(
        state,
        mobile_activity=mobile_activity,
        source_mode=dashboard_app.SOURCE_MOBILE_API,
    )
    camperdown = frame[frame["Station"] == "Camperdown Country Park"].iloc[0]

    assert camperdown["Status"] == "Available"
    assert camperdown["Active / Charging count"] == 0
    assert dashboard_app.effective_active_request_count(state.metrics, mobile_activity) == 0


def test_mobile_station_grouping_matches_confirmed_postgres_active_sessions() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    mobile_activity = dashboard_app.MobileActivitySnapshot(
        active_sessions=_confirmed_active_db_sessions(),
        open_reservations=[],
        session_status_counts={"active": 4},
        user_emails_by_id={},
        db_available=True,
    )

    frame = dashboard_app.active_mobile_sessions_by_station_frame(mobile_activity)
    counts_by_station = dict(zip(frame["Station"], frame["Active sessions"], strict=False))
    metrics = _metrics_snapshot(datetime.fromisoformat("2024-06-10T15:00:00"))

    assert dashboard_app.effective_charging_count(metrics, mobile_activity) == 4
    assert counts_by_station["Dundee Railway Station"] == 1
    assert counts_by_station["Dundee Taybridge Rail Station, South Union Street, Dundee"] == 2
    assert counts_by_station["Alexander Street - Dundee"] == 1


def test_mobile_station_activity_groups_by_charging_session_station_id() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("dundee_railway_station", "Dundee Railway Station"),
            _station_snapshot(
                "dundee_taybridge_rail_station_south_union_street_dundee",
                "Dundee Taybridge Rail Station, South Union Street, Dundee",
            ),
            _station_snapshot("alexander_street_dundee", "Alexander Street - Dundee"),
            _station_snapshot("mill_o_mains_primary_school", "Mill O Mains Primary School"),
        ],
    )
    mobile_activity = dashboard_app.MobileActivitySnapshot(
        active_sessions=_confirmed_active_db_sessions(),
        open_reservations=[
            {
                "reservation_id": "completed-reservation",
                "status": "completed",
                "station_id": "mill_o_mains_primary_school",
                "station_name": "Mill O Mains Primary School",
            }
        ],
        session_status_counts={"active": 4},
        user_emails_by_id={},
        db_available=True,
    )

    frame = dashboard_app.station_activity_frame(
        state,
        mobile_activity=mobile_activity,
        source_mode=dashboard_app.SOURCE_MOBILE_API,
    )
    counts_by_station = dict(zip(frame["Station"], frame["Active / Charging count"], strict=False))
    statuses_by_station = dict(zip(frame["Station"], frame["Status"], strict=False))

    assert counts_by_station["Dundee Railway Station"] == 1
    assert counts_by_station["Dundee Taybridge Rail Station, South Union Street, Dundee"] == 2
    assert counts_by_station["Alexander Street - Dundee"] == 1
    assert counts_by_station["Mill O Mains Primary School"] == 0
    assert statuses_by_station["Mill O Mains Primary School"] == "Available"


def test_raw_active_session_rows_match_dashboard_diagnostics() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    mobile_activity = dashboard_app.MobileActivitySnapshot(
        active_sessions=_confirmed_active_db_sessions(),
        open_reservations=[],
        session_status_counts={"active": 4},
        user_emails_by_id={},
        db_available=True,
    )

    frame = dashboard_app.raw_active_session_rows_frame(mobile_activity)

    assert list(frame.columns) == ["session_id", "email", "station_id", "station_name", "reservation_id", "started_at"]
    assert len(frame) == 4
    assert frame.iloc[0]["station_id"] == "dundee_taybridge_rail_station_south_union_street_dundee"


def test_mapped_station_details_do_not_claim_live_charging_state() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("camperdown_country_park", "Camperdown Country Park"),
        ],
    )
    map_frame = dashboard_app.station_map_frame(state)
    table_frame = dashboard_app.station_map_table_frame(map_frame)

    assert "Charging" not in table_frame.columns
    assert "Queued" not in table_frame.columns
    assert "Load state" in table_frame.columns
    assert "Runtime utilization" in table_frame.columns
    assert "Runtime headroom kW" in table_frame.columns


def test_station_map_marks_normal_busy_congested_station_load_states() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    state = _state_snapshot(
        stations=[
            _station_snapshot("normal_station", "Normal Station"),
            _station_snapshot("busy_station", "Busy Station", active_sessions=1, utilization=0.5),
            _station_snapshot("congested_station", "Congested Station", queue_length=1, utilization=0.9),
        ],
    )

    map_frame = dashboard_app.station_map_frame(state)
    states_by_station = dict(zip(map_frame["station_name"], map_frame["load_state"], strict=False))
    colors_by_station = dict(zip(map_frame["station_name"], map_frame["map_color"], strict=False))

    assert states_by_station == {
        "Normal Station": dashboard_app.LOAD_STATE_NORMAL,
        "Busy Station": dashboard_app.LOAD_STATE_BUSY,
        "Congested Station": dashboard_app.LOAD_STATE_CONGESTED,
    }
    assert colors_by_station["Normal Station"] == dashboard_app.LOAD_STATE_COLORS[dashboard_app.LOAD_STATE_NORMAL]
    assert colors_by_station["Busy Station"] == dashboard_app.LOAD_STATE_COLORS[dashboard_app.LOAD_STATE_BUSY]
    assert colors_by_station["Congested Station"] == dashboard_app.LOAD_STATE_COLORS[dashboard_app.LOAD_STATE_CONGESTED]
    assert {"utilization_label", "wait_label", "headroom_label"}.issubset(map_frame.columns)


def test_recommendation_summary_keeps_full_station_and_cost_text() -> None:
    dashboard_app = importlib.import_module("dashboards.sim_dashboard.app")
    recommendation = RecommendationResponse(
        request_id="external-long-station",
        simulated_timestamp=datetime.fromisoformat("2024-06-10T15:00:00"),
        top_recommendation=RecommendationOption(
            station_id="lochee_charging_hub_aimer_square_dundee",
            station_name="Lochee Charging Hub, Aimer Square, Dundee",
            zone_id="zone_west_lochee",
            transformer_id="tx_west_lochee",
            score=0.81723,
            distance_km=1.2,
            estimated_wait_minutes=4,
            estimated_duration_minutes=37,
            estimated_cost_gbp=12.75,
            transformer_headroom_kw=180.0,
            current_queue=0,
            utilization=0.2,
            charger_compatible=True,
        ),
    )

    frame = dashboard_app.recommendation_summary_frame(recommendation)

    assert frame.iloc[0]["Station"] == "Lochee Charging Hub, Aimer Square, Dundee"
    assert frame.iloc[0]["Score"] == "0.817"
    assert frame.iloc[0]["Wait"] == "4 min"
    assert frame.iloc[0]["Charge time"] == "37 min"
    assert frame.iloc[0]["Cost"] == "GBP 12.75"


def _state_snapshot(
    *,
    stations: list[StationStateSnapshot],
    active_sessions: list[RequestSnapshot] | None = None,
    queued_requests: list[RequestSnapshot] | None = None,
) -> StateSnapshot:
    timestamp = datetime.fromisoformat("2024-06-10T15:00:00")
    return StateSnapshot(
        simulated_timestamp=timestamp,
        active_policy="weighted_score",
        replay_year=2024,
        replay_day="2024-06-10",
        running=True,
        replay_cursor=0,
        replay_total=0,
        active_requests=[],
        queued_requests=queued_requests or [],
        active_sessions=active_sessions or [],
        stations=stations,
        transformers=[],
        metrics=_metrics_snapshot(timestamp),
    )


def _station_snapshot(
    station_id: str,
    station_name: str,
    *,
    active_sessions: int = 0,
    queue_length: int = 0,
    utilization: float = 0.0,
    estimated_wait_minutes: int = 0,
    transformer_headroom_kw: float = 100.0,
) -> StationStateSnapshot:
    return StationStateSnapshot(
        station_id=station_id,
        station_name=station_name,
        zone_id="zone_demo",
        transformer_id="tx_demo",
        latitude=56.46,
        longitude=-2.97,
        cp_count_total=2,
        station_capacity_kw_assumed=50.0,
        active_sessions=active_sessions,
        queue_length=queue_length,
        utilization=utilization,
        estimated_wait_minutes=estimated_wait_minutes,
        transformer_headroom_kw=transformer_headroom_kw,
    )


def _request_snapshot(
    *,
    request_id: str,
    status: str,
    station_id: str,
    station_name: str,
) -> RequestSnapshot:
    arrival_ts = datetime.fromisoformat("2024-06-10T15:00:00")
    return RequestSnapshot(
        request_id=request_id,
        source_type="external_live",
        status=status,
        arrival_ts=arrival_ts,
        latest_finish_ts=arrival_ts + timedelta(minutes=90),
        requested_energy_kwh=30.0,
        requested_duration_minutes=45,
        preference_mode="fastest",
        charger_type_preference="Any",
        station_id=station_id,
        station_name=station_name,
        zone_id="zone_demo",
    )


def _mobile_session(
    session_id: str,
    station_id: str,
    station_name: str,
    *,
    station_capacity: int,
) -> dict:
    return {
        "session_id": session_id,
        "status": "active",
        "station_id": station_id,
        "station_name": station_name,
        "station_capacity": station_capacity,
        "user_email": f"{session_id}@example.edu",
    }


def _confirmed_active_db_sessions() -> list[dict]:
    return [
        _active_db_session(
            "taybridge-02",
            "dundee_taybridge_rail_station_south_union_street_dundee",
            "Dundee Taybridge Rail Station, South Union Street, Dundee",
            "driver2@example.edu",
            "2026-06-19T10:03:00",
        ),
        _active_db_session(
            "taybridge-01",
            "dundee_taybridge_rail_station_south_union_street_dundee",
            "Dundee Taybridge Rail Station, South Union Street, Dundee",
            "driver1@example.edu",
            "2026-06-19T10:02:00",
        ),
        _active_db_session(
            "railway-01",
            "dundee_railway_station",
            "Dundee Railway Station",
            "driver3@example.edu",
            "2026-06-19T10:01:00",
        ),
        _active_db_session(
            "alexander-01",
            "alexander_street_dundee",
            "Alexander Street - Dundee",
            "driver4@example.edu",
            "2026-06-19T10:00:00",
        ),
    ]


def _active_db_session(
    session_id: str,
    station_id: str,
    station_name: str,
    email: str,
    started_at: str,
) -> dict:
    return {
        "session_id": session_id,
        "status": "active",
        "user_id": f"user-{session_id}",
        "email": email,
        "station_id": station_id,
        "station_name": station_name,
        "reservation_id": f"reservation-{session_id}",
        "started_at": started_at,
    }


def _metrics_snapshot(timestamp: datetime) -> MetricsSnapshot:
    return MetricsSnapshot(
        simulated_timestamp=timestamp,
        active_policy="weighted_score",
        active_request_count=0,
        queued_request_count=0,
        active_session_count=0,
        completed_requests_total=0,
        missed_requests_total=0,
        overload_event_count=0,
        queue_length_total=0,
        requests_seen_total=0,
    )
