"""Verify the offline Dundee RL training boundary around the existing RL env."""

from __future__ import annotations

from pathlib import Path
import random
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.rl_training.metrics import summarize_rollouts
from ev_core.rl_training.offline_station_selection_env import OfflineDundeeStationSelectionEnv
from ev_core.rl_training.rollout import choose_random_valid_action, run_random_valid_rollout
from ev_core.rl_training.scenario_factory import OfflineDundeeScenarioFactory, OfflineTrainingScenarioRequest


def main() -> int:
    factory = OfflineDundeeScenarioFactory(repo_root=REPO_ROOT)
    scenario_bundle = factory.build(
        OfflineTrainingScenarioRequest(
            split="train",
            seed=1000,
            duration_hours=1,
            demand_level="normal",
        )
    )
    env = OfflineDundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=scenario_bundle.scenario)

    observation, info = env.reset(seed=scenario_bundle.scenario.seed)
    valid_action_count = sum(1 for allowed in env.valid_action_mask() if allowed)
    first_action = choose_random_valid_action(env, random.Random(scenario_bundle.scenario.seed))
    _, reward, terminated, truncated, _ = env.step(first_action)

    rollout_result = run_random_valid_rollout(
        env,
        seed=scenario_bundle.scenario.seed,
        max_steps=5,
    )
    rollout_summary = summarize_rollouts([rollout_result])

    print("Offline Dundee RL training env verification")
    print(f"scenario_id: {scenario_bundle.scenario.scenario_id}")
    print(f"split: {scenario_bundle.scenario.split}")
    print(f"seed: {scenario_bundle.scenario.seed}")
    print(f"station_count: {len(env.station_ids)}")
    print(f"observation_shape: {observation.shape}")
    print(f"valid_action_count: {valid_action_count}")
    print(f"first_reward_after_random_valid_step: {reward}")
    print(f"terminated_after_first_step: {terminated}")
    print(f"truncated_after_first_step: {truncated}")
    print(f"short_rollout_steps: {rollout_result.steps}")
    print(f"short_rollout_total_reward: {rollout_result.total_reward}")
    print(f"short_rollout_served_count: {rollout_result.served_count}")
    print(f"short_rollout_summary: {rollout_summary}")
    print(f"info_keys: {sorted(info.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
