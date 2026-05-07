from __future__ import annotations

from datetime import datetime

from ev_core.recommender.ranker import CandidateContext
from ev_core.recommender.ranker import RecommendationInput, WeightedHeuristicRanker
from ev_core.recommender.service import RecommendationService


def candidate(station_id: str, *, distance_km: float, wait_minutes: int, cost_gbp: float) -> CandidateContext:
    return CandidateContext(
        station_id=station_id,
        station_name=station_id.replace("_", " ").title(),
        zone_id="zone",
        transformer_id="tx",
        distance_km=distance_km,
        estimated_wait_minutes=wait_minutes,
        estimated_duration_minutes=30,
        estimated_cost_gbp=cost_gbp,
        transformer_headroom_kw=200.0,
        current_queue=0,
        utilization=0.25,
        charger_compatible=True,
        metadata={"connector_mix_total": "rapid"},
    )


def recommend(candidates: list[CandidateContext]):
    return RecommendationService().recommend(
        request_id="request-1",
        client_request_id="client-1",
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=candidates,
    )


def test_recommend_sets_top_and_three_alternatives_from_ranked_options() -> None:
    response = recommend(
        [
            candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0),
            candidate("rank_2", distance_km=0.2, wait_minutes=0, cost_gbp=5.0),
            candidate("rank_3", distance_km=0.3, wait_minutes=0, cost_gbp=5.0),
            candidate("rank_4", distance_km=0.4, wait_minutes=0, cost_gbp=5.0),
            candidate("rank_5", distance_km=0.5, wait_minutes=0, cost_gbp=5.0),
        ]
    )

    assert response.top_recommendation is not None
    assert response.top_recommendation.station_id == "rank_1"
    assert [option.station_id for option in response.alternatives] == ["rank_2", "rank_3", "rank_4"]


def test_empty_candidates_returns_no_top_recommendation_and_existing_congestion_note() -> None:
    response = recommend([])

    assert response.top_recommendation is None
    assert response.alternatives == []
    assert response.congestion_note == "No feasible station matched the request window and charger constraints."


def test_recommendation_response_field_names_remain_unchanged() -> None:
    response = recommend([candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0)])

    assert set(response.model_dump(mode="json")) == {
        "request_id",
        "client_request_id",
        "simulated_timestamp",
        "zone_id",
        "top_recommendation",
        "alternatives",
        "congestion_note",
        "debug_reasoning_summary",
        "source_type",
        "metadata",
    }


def test_custom_ranker_injection_still_works() -> None:
    class FirstOnlyRanker:
        def __init__(self) -> None:
            self.seen_payload: RecommendationInput | None = None

        def rank(self, payload: RecommendationInput):
            self.seen_payload = payload
            return WeightedHeuristicRanker().rank(payload)[:1]

    ranker = FirstOnlyRanker()
    response = RecommendationService(ranker=ranker).recommend(
        request_id="request-1",
        client_request_id="client-1",
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=[
            candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0),
            candidate("rank_2", distance_km=0.2, wait_minutes=0, cost_gbp=5.0),
        ],
    )

    assert ranker.seen_payload is not None
    assert ranker.seen_payload.preference_mode == "closest"
    assert response.top_recommendation is not None
    assert response.top_recommendation.station_id == "rank_1"
    assert response.alternatives == []


def test_default_policy_matches_legacy_weighted_ranker_behavior() -> None:
    candidates = [
        candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0),
        candidate("rank_2", distance_km=0.2, wait_minutes=15, cost_gbp=4.0),
        candidate("rank_3", distance_km=0.3, wait_minutes=30, cost_gbp=3.0),
    ]
    kwargs = {
        "request_id": "request-1",
        "client_request_id": "client-1",
        "simulated_timestamp": datetime(2024, 6, 10, 12, 0),
        "zone_id": "zone",
        "source_type": "external_live",
        "preference_mode": "closest",
        "candidate_contexts": candidates,
    }

    default_response = RecommendationService().recommend(**kwargs)
    legacy_response = RecommendationService(ranker=WeightedHeuristicRanker()).recommend(**kwargs)

    assert default_response.model_dump(mode="json") == legacy_response.model_dump(mode="json")
