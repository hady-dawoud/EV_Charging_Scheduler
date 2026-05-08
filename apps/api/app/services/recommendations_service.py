from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationsResponse,
)
from app.services.runtime_service import inject_live_request


def generate_recommendations(
    request: RecommendationRequest,
    *,
    recommendation_policy_name: str | None = None,
) -> RecommendationsResponse:
    return inject_live_request(
        request,
        recommendation_policy_name=recommendation_policy_name,
    )
