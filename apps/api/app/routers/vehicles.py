from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.vehicles import UserVehicleRead, UserVehicleUpsertRequest
from app.services.vehicles_service import (
    get_or_create_vehicle_for_user,
    upsert_vehicle_for_user,
)

router = APIRouter(
    prefix="/vehicles",
    tags=["vehicles"],
)


@router.get(
    "/me",
    response_model=UserVehicleRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user's vehicle profile",
)
def get_my_vehicle(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserVehicleRead:
    return get_or_create_vehicle_for_user(
        db,
        current_user=current_user,
    )


@router.put(
    "/me",
    response_model=UserVehicleRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user's vehicle profile",
)
def update_my_vehicle(
    request: UserVehicleUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserVehicleRead:
    return upsert_vehicle_for_user(
        db,
        current_user=current_user,
        request=request,
    )
