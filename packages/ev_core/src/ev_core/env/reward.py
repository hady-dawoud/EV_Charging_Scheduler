"""Reward scaffolding for future multi-objective training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardBreakdown:
    """Named reward components tracked per 15-minute environment step."""

    total: float = 0.0
    service_quality: float = 0.0
    grid_cost: float = 0.0
    fairness: float = 0.0


class RewardModel:
    """Placeholder reward calculator for future simulation training loops."""

    def evaluate(self) -> RewardBreakdown:
        """Evaluate the reward terms for a single environment step."""

        raise NotImplementedError("TODO: implement reward shaping logic.")
