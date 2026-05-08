from __future__ import annotations

from ev_core.contracts.responses import RecommendationOption
from ev_core.recommender.baseline_policies import CheapestPolicy, ClosestPolicy, FastestPolicy, OverloadAwarePolicy
from ev_core.recommender.ranker import CandidateContext, RecommendationInput


def candidate(
    station_id: str,
    *,
    distance_km: float = 2.0,
    wait_minutes: int = 15,
    duration_minutes: int = 30,
    cost_gbp: float = 8.0,
    headroom_kw: float = 200.0,
    current_queue: int = 0,
    utilization: float = 0.25,
    compatible: bool = True,
) -> CandidateContext:
    return CandidateContext(
        station_id=station_id,
        station_name=station_id.replace("_", " ").title(),
        zone_id="zone",
        transformer_id="tx",
        distance_km=distance_km,
        estimated_wait_minutes=wait_minutes,
        estimated_duration_minutes=duration_minutes,
        estimated_cost_gbp=cost_gbp,
        transformer_headroom_kw=headroom_kw,
        current_queue=current_queue,
        utilization=utilization,
        charger_compatible=compatible,
        metadata={"connector_mix_total": "ac;rapid"},
    )


def rank_ids(policy, candidates: tuple[CandidateContext, ...]) -> list[str]:
    request = RecommendationInput(request_id="request-1", preference_mode="closest", candidates=candidates)
    return [option.station_id for option in policy.rank(request, candidates)]


def test_closest_policy_prioritizes_distance_with_wait_cost_headroom_tie_breaks() -> None:
    candidates = (
        candidate("far", distance_km=4.0, wait_minutes=0, cost_gbp=1.0, headroom_kw=500.0),
        candidate("near_worse_tie", distance_km=1.0, wait_minutes=10, cost_gbp=4.0, headroom_kw=300.0),
        candidate("near_best_tie", distance_km=1.0, wait_minutes=5, cost_gbp=4.0, headroom_kw=300.0),
        candidate("near_cost_tie", distance_km=1.0, wait_minutes=5, cost_gbp=5.0, headroom_kw=300.0),
        candidate("near_headroom_tie", distance_km=1.0, wait_minutes=5, cost_gbp=4.0, headroom_kw=250.0),
    )

    assert rank_ids(ClosestPolicy(), candidates) == [
        "near_best_tie",
        "near_headroom_tie",
        "near_cost_tie",
        "near_worse_tie",
        "far",
    ]


def test_cheapest_policy_prioritizes_cost_with_distance_wait_headroom_tie_breaks() -> None:
    candidates = (
        candidate("expensive", cost_gbp=9.0, distance_km=0.1, wait_minutes=0, headroom_kw=500.0),
        candidate("cheap_worse_tie", cost_gbp=3.0, distance_km=2.0, wait_minutes=10, headroom_kw=300.0),
        candidate("cheap_best_tie", cost_gbp=3.0, distance_km=1.0, wait_minutes=5, headroom_kw=300.0),
        candidate("cheap_wait_tie", cost_gbp=3.0, distance_km=1.0, wait_minutes=8, headroom_kw=300.0),
        candidate("cheap_headroom_tie", cost_gbp=3.0, distance_km=1.0, wait_minutes=5, headroom_kw=250.0),
    )

    assert rank_ids(CheapestPolicy(), candidates) == [
        "cheap_best_tie",
        "cheap_headroom_tie",
        "cheap_wait_tie",
        "cheap_worse_tie",
        "expensive",
    ]


def test_fastest_policy_prioritizes_total_time_with_wait_duration_distance_tie_breaks() -> None:
    candidates = (
        candidate("slow", wait_minutes=0, duration_minutes=90, distance_km=0.1),
        candidate("fast_worse_tie", wait_minutes=20, duration_minutes=20, distance_km=1.0),
        candidate("fast_best_tie", wait_minutes=10, duration_minutes=30, distance_km=1.0),
        candidate("fast_duration_tie", wait_minutes=10, duration_minutes=30, distance_km=2.0),
    )

    assert rank_ids(FastestPolicy(), candidates) == [
        "fast_best_tie",
        "fast_duration_tie",
        "fast_worse_tie",
        "slow",
    ]


def test_overload_aware_policy_prioritizes_healthy_grid_conditions() -> None:
    candidates = (
        candidate("overloaded_busy", headroom_kw=-10.0, utilization=1.1, current_queue=5, wait_minutes=45, distance_km=0.1),
        candidate("healthy", headroom_kw=450.0, utilization=0.2, current_queue=0, wait_minutes=0, distance_km=4.0),
        candidate("low_headroom", headroom_kw=25.0, utilization=0.2, current_queue=0, wait_minutes=0, distance_km=1.0),
        candidate("busy", headroom_kw=450.0, utilization=0.8, current_queue=4, wait_minutes=30, distance_km=1.0),
    )

    assert rank_ids(OverloadAwarePolicy(), candidates)[0] == "healthy"
    assert rank_ids(OverloadAwarePolicy(), candidates)[-1] == "overloaded_busy"


def test_incompatible_candidates_are_strongly_penalized_but_keep_output_shape() -> None:
    ranked = ClosestPolicy().rank(
        RecommendationInput(request_id="request-1", preference_mode="closest"),
        (
            candidate("incompatible_near", distance_km=0.1, compatible=False),
            candidate("compatible_far", distance_km=5.0, compatible=True),
        ),
    )

    assert ranked[0].station_id == "compatible_far"
    assert all(isinstance(option, RecommendationOption) for option in ranked)
    assert set(ranked[0].model_dump(mode="json")) == {
        "station_id",
        "station_name",
        "zone_id",
        "transformer_id",
        "score",
        "distance_km",
        "estimated_wait_minutes",
        "estimated_duration_minutes",
        "estimated_cost_gbp",
        "transformer_headroom_kw",
        "current_queue",
        "utilization",
        "charger_compatible",
        "reason_tags",
        "metadata",
    }
