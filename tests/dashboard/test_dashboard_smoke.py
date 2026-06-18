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
    history_frame = dashboard_app.recommendation_history_frame(external_requests, recommendations)
    candidate_frame = dashboard_app.recommendation_candidate_frame(recommendations[0])

    assert len(external_requests) == 1
    assert len(recommendations) == 1
    assert history_frame.iloc[0]["Status"] == "matched"
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


def _station_snapshot(station_id: str, station_name: str) -> StationStateSnapshot:
    return StationStateSnapshot(
        station_id=station_id,
        station_name=station_name,
        zone_id="zone_demo",
        transformer_id="tx_demo",
        latitude=56.46,
        longitude=-2.97,
        cp_count_total=2,
        station_capacity_kw_assumed=50.0,
        active_sessions=0,
        queue_length=0,
        utilization=0.0,
        estimated_wait_minutes=0,
        transformer_headroom_kw=100.0,
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
