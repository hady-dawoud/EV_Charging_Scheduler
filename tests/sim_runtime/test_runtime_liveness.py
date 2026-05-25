from __future__ import annotations

import importlib
import sys
from datetime import timedelta
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
    reason="runtime liveness tests require real pandas",
)

from ev_core.contracts.requests import ExternalChargingRequest
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def runtime_manager(case_name: str) -> RuntimeManager:
    repo_root = Path(__file__).resolve().parents[2]
    storage_root = repo_root / "outputs" / "test_runtime" / f"{case_name}_{uuid4().hex}"
    manager = RuntimeManager(repo_root)
    manager.storage = RuntimeStorage(storage_root)
    return manager


def app_like_request(manager: RuntimeManager, index: int) -> ExternalChargingRequest:
    state = manager.get_latest_state()
    assert state is not None
    request_ts = state.simulated_timestamp
    return ExternalChargingRequest(
        client_request_id=f"liveness-client-{index}",
        request_timestamp=request_ts,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=20.0,
        preference_mode="Closest",
        charger_type="DC",
        latest_finish_ts=request_ts + timedelta(hours=3),
        source_type="external_live",
        request_id=f"liveness-request-{index}",
        zone_id="zone_central_waterfront",
        vehicle_max_dc_kw=150.0,
    )


def test_runtime_keeps_recommending_across_multiple_ticks() -> None:
    manager = runtime_manager("liveness")
    manager.start(
        replay_day="2024-06-10",
        start_hour=23,
        start_minute=30,
        runtime_mode="replay",
        warm_start_hours=0,
    )
    timestamps = []
    top_station_ids = []

    for index in range(5):
        manager.tick(steps=1)
        state = manager.get_latest_state()
        assert state is not None
        timestamps.append(state.simulated_timestamp)
        response = manager.recommend(app_like_request(manager, index))
        assert response.top_recommendation is not None
        top_station_ids.append(response.top_recommendation.station_id)

    status = manager.get_runtime_status()
    recent = manager.get_recent_recommendations(limit=5)

    assert timestamps == sorted(timestamps)
    assert len(set(timestamps)) == 5
    assert len(recent) == 5
    assert all(top_station_ids)
    assert status["runtime_status"] == "replay_exhausted"
    assert status["replay_exhausted"] is True
    assert status["terminal_reason"] == "replay_exhausted_no_active_work"
    assert status["recommendation_policy_name"] == "weighted_score"
    assert status["pricing_model"] == "dundee_tariff_plus_dynamic_overlay"
    assert status["routing_provider_name"] == "simple_distance"
