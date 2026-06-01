from __future__ import annotations

import os
from dataclasses import dataclass

KNOWN_RECOMMENDATION_POLICIES = frozenset(
    {'weighted_score', 'closest', 'cheapest', 'fastest', 'overload_aware'}
)


@dataclass(frozen=True)
class RecommendationConfig:
    policy_name: str = 'weighted_score'
    fallback_policy_name: str = 'weighted_score'
    max_alternatives: int = 3


def recommendation_config_from_env() -> RecommendationConfig:
    return RecommendationConfig(
        policy_name=os.getenv('RECOMMENDATION_POLICY_NAME', 'weighted_score'),
        fallback_policy_name=os.getenv('RL_FALLBACK_POLICY_NAME', 'weighted_score'),
    )
