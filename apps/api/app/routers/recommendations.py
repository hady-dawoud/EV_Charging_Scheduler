from fastapi import APIRouter, status

from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationsResponse,
)
from app.services.recommendations_service import generate_recommendations

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
)


@router.post(
    "",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate recommendations",
    description="Return mocked charging station recommendations based on simple filters.",
    response_description="A ranked list of recommendations.",
)
def get_recommendations(
    request: RecommendationRequest,
) -> RecommendationsResponse:
    return RecommendationsResponse(
        recommendations=generate_recommendations(request)
    )