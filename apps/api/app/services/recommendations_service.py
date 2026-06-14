from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationsResponse,
)
from app.services.runtime_service import inject_live_request
from ev_core.contracts.requests import normalize_preference_mode
from ev_core.config.recommendation import select_recommendation_policy


def generate_recommendations(
    request: RecommendationRequest,
    *,
    recommendation_policy_name: str | None = None,
) -> RecommendationsResponse:
    preference_mode = normalize_preference_mode(request.preference_mode)
    selection = select_recommendation_policy(
        preference_mode=preference_mode,
        explicit_policy_name=recommendation_policy_name,
    )
    return inject_live_request(
        request,
        recommendation_policy_name=selection.effective_policy_name,
        policy_selection_metadata=selection.metadata(),
    )
