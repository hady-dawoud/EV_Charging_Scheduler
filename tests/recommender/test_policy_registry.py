from __future__ import annotations

from ev_core.recommender.policy_registry import PolicyRegistry
from ev_core.recommender.ranker import CandidateContext, RecommendationInput, WeightedHeuristicRanker


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

