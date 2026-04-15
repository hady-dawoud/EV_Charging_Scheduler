from fastapi import APIRouter, HTTPException, status

from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationsResponse,
)
from app.services.recommendations_service import generate_recommendations
from app.services.runtime_service import RuntimeNotStartedError

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
)


@router.post(
    "",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate live recommendations",
    description="Inject a live external charging request into the simulator runtime and return the generated recommendation bundle.",
    response_description="A simulator-generated recommendation response.",
)
def get_recommendations(
    request: RecommendationRequest,
) -> RecommendationsResponse:
    try:
        return generate_recommendations(request)
    except RuntimeNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc