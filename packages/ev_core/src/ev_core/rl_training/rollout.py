"""Offline rollout helpers with no SB3 dependency."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import random

from ev_core.recommender.policy_registry import PolicyRegistry

from .offline_station_selection_env import OfflineDundeeStationSelectionEnv


@dataclass(frozen=True)
class RolloutResult:
    scenario_id: str
    policy_name: str
    total_reward: float
    steps: int
    served_count: int
    invalid_action_count: int
    missed_count: int


def choose_random_valid_action(env: OfflineDundeeStationSelectionEnv, rng: random.Random) -> int:
    valid_actions = [index for index, allowed in enumerate(env.valid_action_mask()) if allowed]
    if not valid_actions:
        return 0
    return valid_actions[rng.randrange(len(valid_actions))]


def select_recommendation_policy_action(env: OfflineDundeeStationSelectionEnv, *, policy_name: str) -> int:
    if env.current_request is None or not env.current_candidate_contexts:
        return 0
    policy = PolicyRegistry().get(policy_name)
    options = policy.rank(request=env.current_request, candidates=env.current_candidate_contexts, runtime_context=None)
    if not options:
        return 0
    best_station_id = options[0].station_id
    try:
        return env.station_ids.index(best_station_id)
    except ValueError:
        return 0


def run_rollout(
    env: OfflineDundeeStationSelectionEnv,
    *,
    policy_name: str,
    action_selector: Callable[[OfflineDundeeStationSelectionEnv], int],
    seed: int | None = None,
    max_steps: int | None = None,
) -> RolloutResult:
    env.reset(seed=seed)
    total_reward = 0.0
    steps = 0
    served_count = 0
    invalid_action_count = 0
    missed_count = 0

    terminated = False
    while not terminated and (max_steps is None or steps < max_steps):
        action = int(action_selector(env))
        _, reward, terminated, _, info = env.step(action)
        total_reward += float(reward)
        steps += 1
        invalid_action_count += int(bool(info.get("invalid_action")))
        missed_count += int(bool(info.get("missed")))
        served_count += int(info.get("selected_station_id") is not None and not info.get("invalid_action") and not info.get("missed"))

    return RolloutResult(
        scenario_id=env.scenario.scenario_id,
        policy_name=policy_name,
        total_reward=round(total_reward, 6),
        steps=steps,
        served_count=served_count,
        invalid_action_count=invalid_action_count,
        missed_count=missed_count,
    )


def run_random_valid_rollout(
    env: OfflineDundeeStationSelectionEnv,
    *,
    seed: int = 0,
    max_steps: int | None = None,
) -> RolloutResult:
    rng = random.Random(seed)
    return run_rollout(
        env,
        policy_name="random_valid",
        action_selector=lambda current_env: choose_random_valid_action(current_env, rng),
        seed=seed,
        max_steps=max_steps,
    )


def run_fixed_action_rollout(
    env: OfflineDundeeStationSelectionEnv,
    *,
    action: int = 0,
    seed: int | None = None,
    max_steps: int | None = None,
) -> RolloutResult:
    return run_rollout(
        env,
        policy_name=f"fixed_action_{action}",
        action_selector=lambda _env: action,
        seed=seed,
        max_steps=max_steps,
    )


def run_recommendation_policy_rollout(
    env: OfflineDundeeStationSelectionEnv,
    *,
    policy_name: str = "weighted_score",
    seed: int | None = None,
    max_steps: int | None = None,
) -> RolloutResult:
    return run_rollout(
        env,
        policy_name=policy_name,
        action_selector=lambda current_env: select_recommendation_policy_action(current_env, policy_name=policy_name),
        seed=seed,
        max_steps=max_steps,
    )


__all__ = [
    "RolloutResult",
    "choose_random_valid_action",
    "run_fixed_action_rollout",
    "run_random_valid_rollout",
    "run_recommendation_policy_rollout",
    "run_rollout",
    "select_recommendation_policy_action",
]
