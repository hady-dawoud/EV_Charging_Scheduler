"""Registry for recommendation ranking policies."""

from __future__ import annotations

from .baseline_policies import CheapestPolicy, ClosestPolicy, FastestPolicy, OverloadAwarePolicy, WeightedScorePolicy
from .policies import RecommendationPolicy


class PolicyRegistry:
    """Resolve recommendation policies by stable names."""

    default_policy_name = "weighted_score"
    _policy_types = {
        WeightedScorePolicy.name: WeightedScorePolicy,
        ClosestPolicy.name: ClosestPolicy,
        CheapestPolicy.name: CheapestPolicy,
        FastestPolicy.name: FastestPolicy,
        OverloadAwarePolicy.name: OverloadAwarePolicy,
    }

    def get(self, policy_name: str | None = None) -> RecommendationPolicy:
        name = policy_name or self.default_policy_name
        policy_type = self._policy_types.get(name)
        if policy_type is not None:
            return policy_type()
        raise ValueError(f"Unsupported recommendation policy: {name}")


__all__ = ["PolicyRegistry"]

