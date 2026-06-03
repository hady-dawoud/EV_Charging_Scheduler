"""Verify the PR3 Gymnasium-compatible RL environment skeleton."""

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

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.rl.env import DundeeStationSelectionEnv
from ev_core.rl.scenarios import RLScenarioSampler


def main() -> int:
    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    sampler = RLScenarioSampler(bundle=bundle)
    scenario = sampler.sample(seed=1000, duration_hours=1, demand_level="normal")
    env = DundeeStationSelectionEnv(repo_root=REPO_ROOT, scenario=scenario, bundle=bundle)

    observation, info = env.reset()
    mask = env.action_masks()
    valid_actions = [index for index, allowed in enumerate(mask) if allowed]
    first_valid = valid_actions[0] if valid_actions else None

    print("RL env skeleton verification")
    print(f"scenario_id: {scenario.scenario_id}")
    print(f"station_count: {len(env.station_ids)}")
    print(f"observation_shape: {observation.shape}")
    print(f"valid_action_count: {len(valid_actions)}")
    print(f"first_valid_action: {first_valid}")

    chosen_action = first_valid if first_valid is not None else 0
    _, reward, terminated, truncated, step_info = env.step(chosen_action)
    print(f"reward_after_one_step: {reward}")
    print(f"terminated_after_one_step: {terminated}")
    print(f"truncated_after_one_step: {truncated}")
    print(f"info_keys: {sorted(step_info.keys())}")

    rollout_steps = 1
    total_reward = reward
    while not terminated and rollout_steps < 10:
        mask = env.action_masks()
        valid_actions = [index for index, allowed in enumerate(mask) if allowed]
        action = valid_actions[random.Random(rollout_steps).randrange(len(valid_actions))] if valid_actions else 0
        _, reward, terminated, _, _ = env.step(action)
        total_reward += reward
        rollout_steps += 1
    print(f"rollout_steps: {rollout_steps}")
    print(f"rollout_total_reward: {round(total_reward, 6)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
