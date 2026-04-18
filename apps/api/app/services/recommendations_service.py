from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationsResponse,
)
from app.services.runtime_service import inject_live_request


def generate_recommendations(
    request: RecommendationRequest,
) -> RecommendationsResponse:
    return inject_live_request(request)