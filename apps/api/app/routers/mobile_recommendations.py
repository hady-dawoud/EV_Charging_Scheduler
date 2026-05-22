from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.mobile_recommendations import MobileRecommendationRequest
from app.schemas.recommendations import RecommendationsResponse
from app.services.mobile_recommendations_service import generate_mobile_recommendations
from app.services.runtime_service import RuntimeNotStartedError

router = APIRouter(
    prefix="/mobile/recommendations",
    tags=["mobile"],
)


@router.post(
    "",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate mobile-friendly recommendations",
    description="Accept a mobile-friendly charging request and translate it into the simulator runtime recommendation contract.",
)
def get_mobile_recommendations(
    request: MobileRecommendationRequest,
    current_user: User = Depends(get_current_user),
) -> RecommendationsResponse:
    try:
        return generate_mobile_recommendations(
            request,
            current_user=current_user,
        )
    except RuntimeNotStartedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
