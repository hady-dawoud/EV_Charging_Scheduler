from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.charging_sessions import ChargingSessionRead
from app.schemas.reservations import (
    ReservationCancelResponse,
    ReservationCreate,
    ReservationRead,
    ReservationsResponse,
)
from app.services.reservations_service import (
    ReservationActiveSessionError,
    ReservationAlreadyCancelledError,
    ReservationNotFoundError,
    ReservationOpenReservationError,
    ReservationStartNotAllowedError,
    ReservationStationNotFoundError,
    cancel_reservation,
    confirm_reservation_start,
    create_reservation,
    list_my_reservations,
)

router = APIRouter(
    prefix="/reservations",
    tags=["reservations"],
)


@router.post(
    "",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create reservation",
)
def create_my_reservation(
    request: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReservationRead:
    try:
        return create_reservation(
            db,
            current_user=current_user,
            request=request,
        )
    except ReservationStationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReservationActiveSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ReservationOpenReservationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/me",
    response_model=ReservationsResponse,
    status_code=status.HTTP_200_OK,
    summary="List my reservations",
)
def get_my_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReservationsResponse:
    return ReservationsResponse(
        reservations=list_my_reservations(
            db,
            current_user=current_user,
        )
    )



@router.post(
    "/{reservation_id}/confirm-start",
    response_model=ChargingSessionRead,
    status_code=status.HTTP_200_OK,
    summary="Confirm reservation start",
)
def confirm_my_reservation_start(
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargingSessionRead:
    try:
        return confirm_reservation_start(
            db,
            current_user=current_user,
            reservation_id=reservation_id,
        )
    except ReservationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReservationStartNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{reservation_id}/cancel",
    response_model=ReservationCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel reservation",
)
def cancel_my_reservation(
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReservationCancelResponse:
    try:
        return cancel_reservation(
            db,
            current_user=current_user,
            reservation_id=reservation_id,
        )
    except ReservationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReservationAlreadyCancelledError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
