from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.rl.contracts import RLEpisodeScenario


REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _bundle():
    return DundeeSimulationRepository(REPO_ROOT).load_bundle()


@pytest.fixture
def gym():
    return pytest.importorskip("gymnasium")


def _small_scenario() -> RLEpisodeScenario:
    from ev_core.rl.scenarios import RLScenarioSampler

    sampler = RLScenarioSampler(bundle=_bundle())
    scenario = sampler.sample(seed=1006, duration_hours=1, demand_level="normal")
    return replace(scenario, request_count=4)


def test_env_imports_when_gymnasium_is_available(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    assert DundeeStationSelectionEnv is not None


def test_reset_returns_observation_and_info(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=_small_scenario())
    observation, info = env.reset()

    assert observation.shape == env.observation_space.shape
    assert "scenario_id" in info


def test_action_space_and_observation_space_match_reset_output(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=_small_scenario())
    observation, _ = env.reset()

    assert env.action_space.n == len(env.station_ids)
    assert env.observation_space.contains(observation)


def test_action_masks_returns_bool_mask_for_each_station(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=_small_scenario())
    env.reset()
    mask = env.action_masks()

    assert len(mask) == len(env.station_ids)
    assert all(isinstance(value, (bool, type(mask[0]))) for value in mask)


def test_valid_action_step_returns_numeric_reward(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=_small_scenario())
    env.reset()
    mask = env.action_masks()
    valid_action = next(index for index, allowed in enumerate(mask) if allowed)

    _, reward, terminated, truncated, info = env.step(valid_action)

    assert isinstance(reward, float)
    assert terminated in {True, False}
    assert truncated is False
    assert "reward_breakdown" in info


def test_invalid_action_gives_negative_reward(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=_small_scenario())
    env.reset()
    mask = env.action_masks()
    invalid_action = next(index for index, allowed in enumerate(mask) if not allowed)

    _, reward, _, _, info = env.step(invalid_action)

    assert reward < 0.0
    assert info["invalid_action"] is True


def test_episode_terminates_after_generated_requests_are_exhausted(gym) -> None:
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=_small_scenario())
    env.reset()

    terminated = False
    steps = 0
    while not terminated and steps < 10:
        mask = env.action_masks()
        action = next((index for index, allowed in enumerate(mask) if allowed), 0)
        _, _, terminated, _, _ = env.step(action)
        steps += 1

    assert terminated is True
