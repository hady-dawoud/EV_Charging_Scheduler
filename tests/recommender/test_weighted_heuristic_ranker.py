from __future__ import annotations

from ev_core.recommender.ranker import CandidateContext, RecommendationInput, WeightedHeuristicRanker


def candidate(
    station_id: str,
    *,
    distance_km: float = 2.0,
    wait_minutes: int = 30,
    duration_minutes: int = 45,
    cost_gbp: float = 10.0,
    headroom_kw: float = 200.0,
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
        current_queue=0,
        utilization=0.25,
        charger_compatible=compatible,
        metadata={"connector_mix_total": "ac;rapid"},
    )


def rank_ids(preference_mode: str, candidates: tuple[CandidateContext, ...]) -> list[str]:
    ranked = WeightedHeuristicRanker().rank(
        RecommendationInput(
            request_id="request-1",
            preference_mode=preference_mode,
            candidates=candidates,
        )
    )
    return [option.station_id for option in ranked]


def preference_candidates() -> tuple[CandidateContext, ...]:
    return (
        candidate("near_option", distance_km=0.1, wait_minutes=45, duration_minutes=60, cost_gbp=20.0),
        candidate("cheap_option", distance_km=5.0, wait_minutes=45, duration_minutes=60, cost_gbp=1.0),
        candidate("fast_option", distance_km=5.0, wait_minutes=0, duration_minutes=15, cost_gbp=20.0),
    )


def test_ranks_candidates_deterministically() -> None:
    candidates = preference_candidates()

    first = rank_ids("fastest", candidates)
    second = rank_ids("fastest", candidates)

    assert first == second


def test_preference_mode_affects_ordering() -> None:
    candidates = preference_candidates()

    assert rank_ids("closest", candidates)[0] == "near_option"
    assert rank_ids("cheapest", candidates)[0] == "cheap_option"
    assert rank_ids("fastest", candidates)[0] == "fast_option"


def test_unknown_preference_mode_defaults_to_fastest() -> None:
    candidates = preference_candidates()

    assert rank_ids("not_a_mode", candidates) == rank_ids("fastest", candidates)


def test_reason_tags_are_generated_from_thresholds() -> None:
    ranked = WeightedHeuristicRanker().rank(
        RecommendationInput(
            request_id="request-1",
            preference_mode="closest",
            candidates=(
                candidate(
                    "tagged",
                    distance_km=1.5,
                    wait_minutes=15,
                    duration_minutes=30,
                    cost_gbp=6.0,
                    headroom_kw=100.0,
                    compatible=True,
                ),
            ),
        )
    )

    assert ranked[0].reason_tags == ["nearby", "low_wait", "high_headroom", "low_cost"]


def test_charger_match_reason_tag_is_generated_when_room_remains() -> None:
    ranked = WeightedHeuristicRanker().rank(
        RecommendationInput(
            request_id="request-1",
            preference_mode="closest",
            candidates=(
                candidate(
                    "charger_match_only",
                    distance_km=2.0,
                    wait_minutes=30,
                    duration_minutes=30,
                    cost_gbp=7.0,
                    headroom_kw=99.0,
                    compatible=True,
                ),
            ),
        )
    )

    assert ranked[0].reason_tags == ["charger_match"]


def test_sort_tie_breaks_after_descending_score() -> None:
    class ConstantScoreRanker(WeightedHeuristicRanker):
        def _score_candidate(self, candidate: CandidateContext, weights: dict[str, float]) -> float:
            return 1.0

    candidates = (
        candidate("wait_30_distance_2_cost_8", wait_minutes=30, distance_km=2.0, cost_gbp=8.0),
        candidate("wait_15_distance_4_cost_8", wait_minutes=15, distance_km=4.0, cost_gbp=8.0),
        candidate("wait_15_distance_2_cost_9", wait_minutes=15, distance_km=2.0, cost_gbp=9.0),
        candidate("wait_15_distance_2_cost_7", wait_minutes=15, distance_km=2.0, cost_gbp=7.0),
    )

    ranked = ConstantScoreRanker().rank(
        RecommendationInput(request_id="request-1", preference_mode="closest", candidates=candidates)
    )

    assert [option.station_id for option in ranked] == [
        "wait_15_distance_2_cost_7",
        "wait_15_distance_2_cost_9",
        "wait_15_distance_4_cost_8",
        "wait_30_distance_2_cost_8",
    ]
