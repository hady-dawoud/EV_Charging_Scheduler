from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def gym():
    return pytest.importorskip("gymnasium")


def test_random_valid_rollout_runs_without_invalid_actions(gym) -> None:
    from ev_core.rl_training.offline_station_selection_env import OfflineDundeeStationSelectionEnv
    from ev_core.rl_training.rollout import run_random_valid_rollout
    from ev_core.rl_training.scenario_factory import OfflineDundeeScenarioFactory, OfflineTrainingScenarioRequest

    factory = OfflineDundeeScenarioFactory(repo_root=REPO_ROOT)
    scenario_bundle = factory.build(OfflineTrainingScenarioRequest(seed=1002, duration_hours=1, demand_level="normal"))
    env = OfflineDundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=scenario_bundle.scenario)

    result = run_random_valid_rollout(env, seed=scenario_bundle.scenario.seed, max_steps=5)

    assert result.policy_name == "random_valid"
    assert result.steps > 0
    assert result.invalid_action_count == 0


def test_rollout_metrics_summarize_multiple_results() -> None:
    from ev_core.rl_training.metrics import summarize_rollouts
    from ev_core.rl_training.rollout import RolloutResult

    summary = summarize_rollouts(
        [
            RolloutResult(
                scenario_id="scenario-a",
                policy_name="random_valid",
                total_reward=3.0,
                steps=4,
                served_count=3,
                invalid_action_count=0,
                missed_count=1,
            ),
            RolloutResult(
                scenario_id="scenario-b",
                policy_name="closest",
                total_reward=1.0,
                steps=2,
                served_count=1,
                invalid_action_count=1,
                missed_count=0,
            ),
        ]
    )

    assert summary["average_reward"] == 2.0
    assert summary["average_steps"] == 3.0
    assert summary["average_invalid_action_count"] == 0.5
