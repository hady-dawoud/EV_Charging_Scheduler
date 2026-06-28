from __future__ import annotations

from ev_core.recommender.feeder_rl_policy import FeederMaskablePPORuntimePolicy
from ev_core.recommender.policy_registry import PolicyRegistry


def test_feeder_rl_policy_is_registered_separately_from_dundee_policy() -> None:
    policy = PolicyRegistry().get("rl_maskable_ppo_feeder")

    assert isinstance(policy, FeederMaskablePPORuntimePolicy)
    assert policy.name == "rl_maskable_ppo_feeder"
