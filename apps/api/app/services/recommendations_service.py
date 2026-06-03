from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationsResponse,
)
from app.services.runtime_service import inject_live_request
from ev_core.contracts.requests import normalize_preference_mode


def generate_recommendations(
    request: RecommendationRequest,
    *,
    recommendation_policy_name: str | None = None,
) -> RecommendationsResponse:
    policy_name = recommendation_policy_name or normalize_preference_mode(request.preference_mode)
    return inject_live_request(
        request,
        recommendation_policy_name=policy_name,
    )
