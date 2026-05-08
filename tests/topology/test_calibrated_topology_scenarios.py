from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.topology.capacity_calibration import build_capacity_recommendations
from ev_core.topology.scenarios import load_topology_scenario
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = REPO_ROOT / "data" / "processed" / "topology_scenarios"


@pytest.mark.parametrize(
    "scenario_name",
    ("dundee_synthetic_v1_realistic.json", "dundee_synthetic_v1_stress.json"),
)
def test_calibrated_scenario_files_load_and_map_stations(scenario_name: str) -> None:
    scenario = load_topology_scenario(SCENARIO_DIR / scenario_name)
    transformer_ids = {transformer.transformer_id for transformer in scenario.transformers}

    assert scenario.transformers
    assert scenario.station_to_transformer
    assert set(scenario.station_to_transformer.values()) <= transformer_ids
    assert all(transformer.capacity_kw > 0 for transformer in scenario.transformers)


def test_realistic_scenario_capacity_is_not_below_max_single_cp_load() -> None:
    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    recommendations = {
        recommendation.transformer_id: recommendation
        for recommendation in build_capacity_recommendations(
            station_rows=bundle.stations,
            chargepoint_rows=bundle.chargepoints,
            transformer_rows=bundle.transformers,
        )
    }
    scenario = load_topology_scenario(SCENARIO_DIR / "dundee_synthetic_v1_realistic.json")

    for transformer in scenario.transformers:
        assert transformer.capacity_kw >= recommendations[transformer.transformer_id].max_single_cp_kw
        if recommendations[transformer.transformer_id].attached_station_count > 1:
            assert transformer.capacity_kw >= 300.0


@pytest.mark.parametrize(
    "scenario_id",
    ("dundee_synthetic_v1_realistic", "dundee_synthetic_v1_stress"),
)
def test_runtime_starts_with_calibrated_topology_scenario(scenario_id: str) -> None:
    manager = RuntimeManager(REPO_ROOT, config=RuntimeConfig(topology_scenario_id=scenario_id))
    manager.storage = RuntimeStorage(REPO_ROOT / "outputs" / "test_runtime" / f"{scenario_id}_{uuid4().hex}")

    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0)
    response = manager.recommend(
        ExternalChargingRequest(
            client_request_id=f"{scenario_id}-request",
            request_timestamp=datetime(2024, 6, 10, 12, 0),
            current_latitude=56.462,
            current_longitude=-2.970,
            requested_energy_kwh=20.0,
            preference_mode="closest",
            charger_type="Any",
            latest_finish_ts=datetime(2024, 6, 10, 15, 0),
            source_type="external_live",
            request_id=f"{scenario_id}-request",
            zone_id="zone_central_waterfront",
        )
    )

    assert len(state.transformers) == 8
    assert response.top_recommendation is not None
