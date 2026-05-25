from __future__ import annotations

import importlib
import sys
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
