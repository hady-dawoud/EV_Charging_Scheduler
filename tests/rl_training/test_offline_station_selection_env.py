from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def gym():
    return pytest.importorskip("gymnasium")


def test_offline_wrapper_uses_existing_dundee_station_selection_env(gym) -> None:
    from ev_core.rl_training.offline_station_selection_env import OfflineDundeeStationSelectionEnv
    from ev_core.rl_training.scenario_factory import OfflineDundeeScenarioFactory, OfflineTrainingScenarioRequest

    factory = OfflineDundeeScenarioFactory(repo_root=REPO_ROOT)
    scenario_bundle = factory.build(OfflineTrainingScenarioRequest(seed=1000, duration_hours=1, demand_level="normal"))
    env = OfflineDundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=scenario_bundle.scenario)

    assert env.core_env.__class__.__name__ == "DundeeStationSelectionEnv"
    observation, info = env.reset(seed=scenario_bundle.scenario.seed)

    assert observation.shape == env.observation_space.shape
    assert len(env.action_masks()) == len(env.station_ids)
    assert info["scenario_id"] == scenario_bundle.scenario.scenario_id


def test_offline_wrapper_exposes_valid_action_mask(gym) -> None:
    from ev_core.rl_training.offline_station_selection_env import OfflineDundeeStationSelectionEnv
    from ev_core.rl_training.scenario_factory import OfflineDundeeScenarioFactory, OfflineTrainingScenarioRequest

    factory = OfflineDundeeScenarioFactory(repo_root=REPO_ROOT)
    scenario_bundle = factory.build(OfflineTrainingScenarioRequest(seed=1000, duration_hours=1, demand_level="normal"))
    env = OfflineDundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=scenario_bundle.scenario)
    env.reset(seed=scenario_bundle.scenario.seed)

    mask = env.valid_action_mask()

    assert len(mask) == len(env.station_ids)
    assert all(isinstance(value, (bool, type(mask[0]))) for value in mask)
