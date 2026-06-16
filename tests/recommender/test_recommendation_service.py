from __future__ import annotations

from datetime import datetime

import pytest

from ev_core.contracts.responses import RecommendationOption
from ev_core.recommender.ranker import CandidateContext
from ev_core.recommender.ranker import RecommendationInput, WeightedHeuristicRanker
from ev_core.recommender.scoring_utils import candidate_to_option
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


def test_recommendation_service_merges_hybrid_policy_diagnostics() -> None:
    class DiagnosticPolicy:
        name = "rl_safety_closest"

        def __init__(self) -> None:
            self.last_diagnostics = {}

        def rank(self, request, candidates, runtime_context=None):
            self.last_diagnostics = {
                "final_ranker": "closest",
                "rl_safety_filter_enabled": True,
                "rl_safety_filter_applied": True,
                "rl_safety_filter_mode": "penalty",
                "rl_safety_mapping_mode": "exact_only",
                "rl_safety_filter_penalized_count": 1,
                "rl_safety_filter_blocked_count": 0,
                "rl_safety_filter_fallback_used": False,
                "rl_safety_filter_reason": "rl_safety_filter_applied",
                "fallback_used": False,
            }
            option = candidate_to_option(candidates[0], score=0.5)
            return [
                option.model_copy(
                    update={
                        "metadata": {
                            **option.metadata,
                            "base_preference_score": 0.75,
                            "rl_safety_adjusted_score": 0.5,
                        }
                    }
                )
            ]

    response = RecommendationService(policy=DiagnosticPolicy()).recommend(
        request_id="request-1",
        client_request_id="client-1",
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=[
            candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0)
        ],
        policy_selection_metadata={
            "requested_policy_name": "closest",
            "effective_policy_name": "rl_safety_closest",
            "policy_source": "preference_mode",
        },
    )

    expected_metadata = {
        "requested_policy_name": "closest",
        "effective_policy_name": "rl_safety_closest",
        "policy_source": "preference_mode",
        "preference_mode": "closest",
        "policy_override_used": False,
        "final_ranker": "closest",
        "rl_safety_filter_enabled": True,
        "rl_safety_filter_applied": True,
        "rl_safety_filter_mode": "penalty",
        "rl_safety_mapping_mode": "exact_only",
        "rl_safety_filter_penalized_count": 1,
        "rl_safety_filter_blocked_count": 0,
        "rl_safety_candidates_penalized": 1,
        "rl_safety_candidates_blocked": 0,
        "rl_safety_filter_fallback_used": False,
        "rl_safety_filter_reason": "rl_safety_filter_applied",
        "fallback_used": False,
    }
    assert response.metadata.items() >= expected_metadata.items()
    assert response.top_recommendation is not None
    assert response.top_recommendation.metadata["base_preference_score"] == 0.75
    assert response.top_recommendation.metadata["rl_safety_adjusted_score"] == 0.5


def test_recommendation_service_exposes_fail_closed_safety_diagnostics() -> None:
    class UnavailableSafetyPolicy:
        name = "rl_safety_closest"

        def __init__(self) -> None:
            self.last_diagnostics = {}

        def rank(self, request, candidates, runtime_context=None):
            self.last_diagnostics = {
                "final_ranker": "closest",
                "rl_safety_filter_enabled": True,
                "rl_safety_filter_applied": False,
                "rl_safety_filter_fallback_used": False,
                "rl_safety_filter_reason": "feeder_observation_missing",
            }
            return []

    response = RecommendationService(policy=UnavailableSafetyPolicy()).recommend(
        request_id="request-1",
        client_request_id="client-1",
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=[
            candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0)
        ],
        policy_selection_metadata={
            "effective_policy_name": "rl_safety_closest",
            "rl_safety_filter_mode": "penalty",
            "rl_safety_mapping_mode": "exact_only",
        },
    )

    assert response.top_recommendation is None
    assert response.metadata["rl_safety_candidates_penalized"] == 0
    assert response.metadata["rl_safety_candidates_blocked"] == 0
    assert response.metadata["fallback_used"] is False
    assert response.metadata["rl_safety_filter_mode"] == "penalty"
    assert response.metadata["rl_safety_mapping_mode"] == "exact_only"


def test_recommendation_service_preserves_dynamic_pricing_metadata() -> None:
    priced = candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0)
    priced = CandidateContext(
        **{
            **priced.__dict__,
            "metadata": {
                **priced.metadata,
                "dynamic_pricing_enabled": True,
                "final_price_per_kwh": 0.42,
                "pricing_reason": "transformer_and_congestion_overlay",
            },
        }
    )

    response = recommend([priced])

    assert response.metadata["dynamic_pricing_enabled"] is True
    assert response.top_recommendation is not None
    assert response.top_recommendation.metadata["final_price_per_kwh"] == 0.42
    assert (
        response.top_recommendation.metadata["pricing_reason"]
        == "transformer_and_congestion_overlay"
    )


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


def test_recommendation_service_can_select_named_baseline_policy() -> None:
    response = RecommendationService(policy_name="cheapest").recommend(
        request_id="request-1",
        client_request_id="client-1",
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=[
            candidate("near_expensive", distance_km=0.1, wait_minutes=0, cost_gbp=10.0),
            candidate("far_cheap", distance_km=4.0, wait_minutes=15, cost_gbp=1.0),
            candidate("mid", distance_km=2.0, wait_minutes=15, cost_gbp=2.0),
            candidate("alt_3", distance_km=3.0, wait_minutes=15, cost_gbp=3.0),
            candidate("alt_4", distance_km=5.0, wait_minutes=15, cost_gbp=4.0),
        ],
    )

    assert isinstance(response.top_recommendation, RecommendationOption)
    assert response.top_recommendation.station_id == "far_cheap"
    assert len(response.alternatives) == 3


def test_recommendation_service_per_call_policy_name_overrides_service_default() -> None:
    service = RecommendationService(policy_name="cheapest")

    response = service.recommend(
        request_id="request-1",
        client_request_id="client-1",
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=[
            candidate("near_expensive", distance_km=0.1, wait_minutes=0, cost_gbp=10.0),
            candidate("far_cheap", distance_km=4.0, wait_minutes=15, cost_gbp=1.0),
        ],
        policy_name="closest",
    )

    assert response.top_recommendation is not None
    assert response.top_recommendation.station_id == "near_expensive"


def test_recommendation_service_unknown_per_call_policy_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported recommendation policy: nope"):
        RecommendationService().recommend(
            request_id="request-1",
            client_request_id="client-1",
            simulated_timestamp=datetime(2024, 6, 10, 12, 0),
            zone_id="zone",
            source_type="external_live",
            preference_mode="closest",
            candidate_contexts=[candidate("rank_1", distance_km=0.1, wait_minutes=0, cost_gbp=5.0)],
            policy_name="nope",
        )
