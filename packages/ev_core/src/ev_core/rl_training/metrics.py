"""Small aggregation helpers for offline RL training rollouts."""

from __future__ import annotations

from collections.abc import Sequence

from .rollout import RolloutResult


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(float(value) for value in values) / len(values)


def summarize_rollouts(results: Sequence[RolloutResult]) -> dict[str, float]:
    if not results:
        return {
            "average_reward": 0.0,
            "average_served_count": 0.0,
            "average_invalid_action_count": 0.0,
            "average_missed_count": 0.0,
            "average_steps": 0.0,
        }
    return {
        "average_reward": round(_mean([result.total_reward for result in results]), 6),
        "average_served_count": round(_mean([result.served_count for result in results]), 6),
        "average_invalid_action_count": round(_mean([result.invalid_action_count for result in results]), 6),
        "average_missed_count": round(_mean([result.missed_count for result in results]), 6),
        "average_steps": round(_mean([result.steps for result in results]), 6),
    }


__all__ = ["summarize_rollouts"]
