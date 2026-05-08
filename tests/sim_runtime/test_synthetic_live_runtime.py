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
    reason="synthetic-live runtime tests require real pandas",
)

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def test_synthetic_live_request_can_use_runtime_recommendation_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bundle = DundeeSimulationRepository(repo_root).load_bundle()
    generator = SyntheticLiveRequestGenerator(
        request_generator_params=bundle.request_generator_params,
        stations=bundle.stations.to_dict(orient="records"),
        seed="runtime-smoke",
    )
    request = generator.generate_one(datetime(2024, 6, 10, 12, 0), index=1)

    manager = RuntimeManager(repo_root)
    manager.storage = RuntimeStorage(repo_root / "outputs" / "test_runtime" / f"synthetic_live_{uuid4().hex}")
    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    response = manager.recommend(request)

    station_ids = {station.station_id for station in state.stations}
    assert response.request_id == request.request_id
    assert response.top_recommendation is not None
    assert response.top_recommendation.station_id in station_ids
    assert request.metadata["generator_type"] == "synthetic_live"
