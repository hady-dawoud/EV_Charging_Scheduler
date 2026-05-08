from __future__ import annotations

from datetime import datetime
import importlib
from pathlib import Path
import sys
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
    reason="runtime smoke tests require real pandas",
)

from ev_core.contracts.requests import ExternalChargingRequest
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


POLICIES = ("weighted_score", "closest", "cheapest", "fastest", "overload_aware")


def mobile_style_request(request_id: str = "runtime-smoke-request") -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id=request_id,
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.970,
        requested_energy_kwh=20.0,
        preference_mode="closest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id=request_id,
        zone_id="zone_central_waterfront",
    )


def runtime_manager(case_name: str) -> RuntimeManager:
    repo_root = Path(__file__).resolve().parents[2]
    storage_root = repo_root / "outputs" / "test_runtime" / f"{case_name}_{uuid4().hex}"
    manager = RuntimeManager(repo_root)
    manager.storage = RuntimeStorage(storage_root)
    return manager


def test_runtime_manager_starts_and_produces_live_recommendation() -> None:
    manager = runtime_manager("runtime_smoke")

    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    response = manager.inject_request(mobile_style_request())

    station_ids = {station.station_id for station in state.stations}
    assert len(state.stations) > 0
    assert len(state.transformers) > 0
    assert response.request_id == "runtime-smoke-request"
    assert response.top_recommendation is not None
    assert len(response.alternatives) <= 3
    assert response.top_recommendation.station_id in station_ids
    assert manager.get_recent_recommendations(limit=1)


def test_runtime_manager_uses_simple_distance_routing_by_default() -> None:
    manager = runtime_manager("routing_provider_default")

    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    env = manager._load_env()

    assert env.routing_provider.name == "simple_distance"


def test_runtime_policy_sweep_produces_recommendation_for_each_policy() -> None:
    manager = runtime_manager("policy_sweep")
    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    station_ids = {station.station_id for station in state.stations}

    for policy in POLICIES:
        response = manager.recommend(
            mobile_style_request(request_id=f"runtime-smoke-{policy}"),
            recommendation_policy_name=policy,
        )

        assert response.top_recommendation is not None
        assert response.top_recommendation.station_id in station_ids
        assert len(response.alternatives) <= 3
