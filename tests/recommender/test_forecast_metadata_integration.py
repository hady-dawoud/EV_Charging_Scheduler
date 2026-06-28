from __future__ import annotations

from datetime import datetime

from ev_core.recommender.ranker import CandidateContext
from ev_core.recommender.service import RecommendationService


def candidate(station_id: str, *, distance_km: float) -> CandidateContext:
    return CandidateContext(
        station_id=station_id,
        station_name=station_id,
        zone_id="zone",
        transformer_id="tx",
        distance_km=distance_km,
        estimated_wait_minutes=0,
        estimated_duration_minutes=30,
        estimated_cost_gbp=5.0,
        transformer_headroom_kw=200.0,
        current_queue=0,
        utilization=0.1,
        charger_compatible=True,
    )


def test_forecast_metadata_reaches_response_and_options_without_changing_order() -> None:
    contexts = [
        candidate("farther", distance_km=5.0),
        candidate("nearer", distance_km=1.0),
    ]
    forecast_metadata = {
        "forecast_provider": "keras_load_kw_30min",
        "forecast_status": "smoke_template",
        "forecast_ranking_mode": "metadata_only",
        "forecast_used_for_ranking": False,
        "forecast_feature_assembly": "smoke_template",
        "forecast_is_production": False,
    }

    without_forecast = RecommendationService().recommend(
        request_id="request-1",
        client_request_id=None,
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=contexts,
        policy_name="closest",
    )
    with_forecast = RecommendationService().recommend(
        request_id="request-1",
        client_request_id=None,
        simulated_timestamp=datetime(2024, 6, 10, 12, 0),
        zone_id="zone",
        source_type="external_live",
        preference_mode="closest",
        candidate_contexts=contexts,
        policy_name="closest",
        runtime_context={"forecast_metadata": forecast_metadata},
    )

    assert without_forecast.top_recommendation is not None
    assert with_forecast.top_recommendation is not None
    assert with_forecast.top_recommendation.station_id == without_forecast.top_recommendation.station_id
    assert with_forecast.metadata["forecast_provider"] == "keras_load_kw_30min"
    assert with_forecast.top_recommendation.metadata["forecast_status"] == "smoke_template"
    assert with_forecast.top_recommendation.metadata["forecast_used_for_ranking"] is False
