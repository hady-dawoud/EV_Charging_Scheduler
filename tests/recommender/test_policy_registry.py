from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from ev_core.recommender.policy_registry import PolicyRegistry
from ev_core.recommender.feeder_rl_policy import FeederMaskablePPORuntimePolicy
from ev_core.recommender.ranker import CandidateContext, RecommendationInput, WeightedHeuristicRanker
from ev_core.recommender.rl_safety_filter import (
    RLSafetyCheapestPolicy,
    RLSafetyClosestPolicy,
    RLSafetyFastestPolicy,
    RLSafetyPreferencePolicy,
    RLSafetyWeightedPolicy,
)


def candidate(station_id: str) -> CandidateContext:
    return CandidateContext(
        station_id=station_id,
        station_name=station_id,
        zone_id="zone",
        transformer_id="tx",
        distance_km=1.0,
        estimated_wait_minutes=0,
        estimated_duration_minutes=15,
        estimated_cost_gbp=5.0,
        transformer_headroom_kw=200.0,
        current_queue=0,
        utilization=0.1,
        charger_compatible=True,
    )


def test_weighted_score_policy_preserves_weighted_heuristic_output() -> None:
    candidates = (candidate("a"), candidate("b"))
    request = RecommendationInput(request_id="request-1", preference_mode="fastest", candidates=candidates)

    policy = PolicyRegistry().get()

    assert policy.name == "weighted_score"
    assert policy.rank(request, candidates) == WeightedHeuristicRanker().rank(request)


def test_policy_registry_returns_weighted_score_by_name() -> None:
    policy = PolicyRegistry().get("weighted_score")

    assert policy.name == "weighted_score"


def test_policy_registry_returns_all_recommendation_baselines_by_name() -> None:
    registry = PolicyRegistry()

    assert registry.get("closest").name == "closest"
    assert registry.get("cheapest").name == "cheapest"
    assert registry.get("fastest").name == "fastest"
    assert registry.get("overload_aware").name == "overload_aware"


def test_policy_registry_default_remains_weighted_score() -> None:
    assert PolicyRegistry.default_policy_name == "weighted_score"
    assert PolicyRegistry().get().name == "weighted_score"


def test_policy_registry_rejects_unknown_policy_name() -> None:
    with pytest.raises(ValueError, match="Unsupported recommendation policy: nope"):
        PolicyRegistry().get("nope")


@pytest.mark.parametrize(
    ("policy_name", "policy_type"),
    [
        ("rl_safety_closest", RLSafetyClosestPolicy),
        ("rl_safety_cheapest", RLSafetyCheapestPolicy),
        ("rl_safety_fastest", RLSafetyFastestPolicy),
        ("rl_safety_weighted", RLSafetyWeightedPolicy),
        ("rl_safety_preference", RLSafetyPreferencePolicy),
    ],
)
def test_policy_registry_returns_rl_safety_hybrid_policies(
    policy_name: str,
    policy_type: type,
) -> None:
    policy = PolicyRegistry().get(policy_name)

    assert type(policy) is policy_type
    assert policy.name == policy_name


def test_policy_registry_import_does_not_import_optional_ml_packages() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": str(Path("packages/ev_core/src").resolve()),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import ev_core.recommender.policy_registry; "
                "forbidden = {'torch', 'stable_baselines3', 'sb3_contrib'}; "
                "loaded = sorted(name for name in forbidden if name in sys.modules); "
                "assert not loaded, loaded"
            ),
        ],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_feeder_rl_policy_fail_closed_returns_no_options_when_checkpoint_missing(monkeypatch) -> None:
    monkeypatch.setenv("RL_POLICY_FAIL_CLOSED", "true")
    monkeypatch.delenv("RL_FEEDER_CHECKPOINT_PATH", raising=False)
    candidates = (candidate("a"), candidate("b"))
    request = RecommendationInput(request_id="request-1", preference_mode="fastest", candidates=candidates)

    result = FeederMaskablePPORuntimePolicy().rank(request, candidates, runtime_context={})

    assert result == []


def test_feeder_rl_policy_fallback_marks_option_metadata(monkeypatch) -> None:
    monkeypatch.delenv("RL_POLICY_FAIL_CLOSED", raising=False)
    monkeypatch.delenv("RL_FEEDER_CHECKPOINT_PATH", raising=False)
    candidates = (candidate("a"), candidate("b"))
    request = RecommendationInput(request_id="request-1", preference_mode="fastest", candidates=candidates)

    result = FeederMaskablePPORuntimePolicy().rank(request, candidates, runtime_context={"feeder_context_available": False})

    assert result
    assert result[0].metadata["fallback_used"] is True
    assert result[0].metadata["rl_policy_scope"] == "digitaltwin_feeder_public_ev"
