"""Registry for recommendation ranking policies."""

from __future__ import annotations

from .baseline_policies import CheapestPolicy, ClosestPolicy, FastestPolicy, OverloadAwarePolicy, WeightedScorePolicy
from .feeder_rl_policy import FeederMaskablePPORuntimePolicy
from .policies import RecommendationPolicy
from .rl_policy import MaskablePPORuntimePolicy
from .rl_safety_filter import (
    RLSafetyCheapestPolicy,
    RLSafetyClosestPolicy,
    RLSafetyFastestPolicy,
    RLSafetyPreferencePolicy,
    RLSafetyWeightedPolicy,
)


class PolicyRegistry:
    """Resolve recommendation policies by stable names."""

    default_policy_name = "weighted_score"
    _policy_types = {
        WeightedScorePolicy.name: WeightedScorePolicy,
        ClosestPolicy.name: ClosestPolicy,
        CheapestPolicy.name: CheapestPolicy,
        FastestPolicy.name: FastestPolicy,
        OverloadAwarePolicy.name: OverloadAwarePolicy,
        MaskablePPORuntimePolicy.name: MaskablePPORuntimePolicy,
        FeederMaskablePPORuntimePolicy.name: FeederMaskablePPORuntimePolicy,
        RLSafetyClosestPolicy.name: RLSafetyClosestPolicy,
        RLSafetyCheapestPolicy.name: RLSafetyCheapestPolicy,
        RLSafetyFastestPolicy.name: RLSafetyFastestPolicy,
        RLSafetyWeightedPolicy.name: RLSafetyWeightedPolicy,
        RLSafetyPreferencePolicy.name: RLSafetyPreferencePolicy,
    }

    def get(self, policy_name: str | None = None) -> RecommendationPolicy:
        name = policy_name or self.default_policy_name
        policy_type = self._policy_types.get(name)
        if policy_type is not None:
            return policy_type()
        raise ValueError(f"Unsupported recommendation policy: {name}")


__all__ = ["PolicyRegistry"]

