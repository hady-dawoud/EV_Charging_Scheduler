from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.topology.scenarios import load_topology_scenario


def test_default_example_topology_scenario_loads() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scenario = DundeeSimulationRepository(repo_root).load_topology_scenario("dundee_synthetic_v1")

    assert scenario.scenario_id == "dundee_synthetic_v1"
    assert scenario.transformers
    assert scenario.station_to_transformer


def test_required_fields_are_validated() -> None:
    bad_path = Path(__file__).resolve().parents[2] / "outputs" / "test_data" / f"bad_topology_{uuid4().hex}.json"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text(json.dumps({"scenario_id": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required fields"):
        load_topology_scenario(bad_path)


def test_missing_scenario_file_raises_clear_error() -> None:
    missing_path = Path(__file__).resolve().parents[2] / "outputs" / "test_data" / f"missing_topology_{uuid4().hex}.json"
    with pytest.raises(FileNotFoundError, match="Topology scenario file not found"):
        load_topology_scenario(missing_path)
