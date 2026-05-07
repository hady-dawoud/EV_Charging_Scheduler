"""Registry for recommendation ranking policies."""

from __future__ import annotations

from .baseline_policies import WeightedScorePolicy
from .policies import RecommendationPolicy


class PolicyRegistry:
    """Resolve recommendation policies by stable names."""

    default_policy_name = "weighted_score"

    def get(self, policy_name: str | None = None) -> RecommendationPolicy:
        name = policy_name or self.default_policy_name
        if name == WeightedScorePolicy.name:
            return WeightedScorePolicy()
        raise ValueError(f"Unsupported recommendation policy: {name}")


__all__ = ["PolicyRegistry"]

