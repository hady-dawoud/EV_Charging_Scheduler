from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from ev_core.data.repositories import DundeeDataBundle
from ev_core.env.environment import DundeeEnv
from ev_core.topology.scenarios import TopologyScenario, TransformerScenario
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def _minimal_bundle() -> DundeeDataBundle:
    stations = pd.DataFrame(
        [
            {
                "station_id": "station_a",
                "station_name": "Station A",
                "zone_id": "zone_a",
                "transformer_id": "tx_a",
                "latitude": 56.46,
                "longitude": -2.97,
                "cp_count_total": 1,
                "connector_mix_total": "ac",
                "station_capacity_kw_assumed": 22.0,
            },
            {
                "station_id": "station_b",
                "station_name": "Station B",
                "zone_id": "zone_a",
                "transformer_id": "tx_a",
                "latitude": 56.47,
                "longitude": -2.98,
                "cp_count_total": 1,
                "connector_mix_total": "ac",
                "station_capacity_kw_assumed": 22.0,
            },
        ]
    )
    transformers = pd.DataFrame(
        [
            {
                "transformer_id": "tx_a",
                "transformer_name": "Transformer A",
                "zone_id": "zone_a",
                "transformer_capacity_kw_assumed": 100.0,
            }
        ]
    )
    replay = pd.DataFrame(
        [
            {
                "request_id": "request_a",
                "arrival_slot": pd.Timestamp("2024-06-10T12:00:00"),
            }
        ]
    )
    return DundeeDataBundle(
        stations=stations,
        transformers=transformers,
        zones=pd.DataFrame([{"zone_id": "zone_a"}]),
        chargepoints=pd.DataFrame(),
        replay_requests_2023=replay,
        replay_requests_2024=replay,
        request_generator_params={},
        background_load=pd.DataFrame(),
        price_table=pd.DataFrame(),
        pv_profile=pd.DataFrame(),
    )


def test_dundee_env_preserves_default_topology_without_scenario() -> None:
    env = DundeeEnv(_minimal_bundle(), start_time=datetime(2024, 6, 10, 12, 0))

    assert env.station_index["station_a"].transformer_id == "tx_a"
    assert env.transformer_index["tx_a"].capacity_kw == 100.0


def test_dundee_env_applies_topology_scenario_overrides() -> None:
    scenario = TopologyScenario(
        scenario_id="scenario_a",
        scenario_name="Scenario A",
        source="test",
        transformers=(
            TransformerScenario(
                transformer_id="tx_b",
                transformer_name="Transformer B",
                zone_id="zone_a",
                capacity_kw=300.0,
                capacity_derating_factor=0.5,
            ),
        ),
        station_to_transformer={"station_a": "tx_b", "station_b": "tx_b"},
    )

    env = DundeeEnv(
        _minimal_bundle(),
        start_time=datetime(2024, 6, 10, 12, 0),
        topology_scenario=scenario,
    )

    assert env.station_index["station_a"].transformer_id == "tx_b"
    assert env.station_index["station_b"].transformer_id == "tx_b"
    assert env.transformer_index["tx_b"].capacity_kw == 150.0
    assert env.transformer_index["tx_b"].attached_station_ids == ("station_a", "station_b")


def test_runtime_manager_starts_with_optional_topology_scenario() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    storage_root = repo_root / "outputs" / "test_runtime" / f"topology_scenario_{uuid4().hex}"
    manager = RuntimeManager(
        repo_root,
        config=RuntimeConfig(topology_scenario_id="dundee_synthetic_v1"),
    )
    manager.storage = RuntimeStorage(storage_root)

    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0)

    assert manager.topology_scenario is not None
    assert manager.topology_scenario.scenario_id == "dundee_synthetic_v1"
    assert len(state.transformers) == 8
