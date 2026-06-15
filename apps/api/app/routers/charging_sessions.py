from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.charging_sessions import (
    ActiveChargingSessionResponse,
    ChargingSessionCompleteRequest,
    ChargingSessionCreate,
    ChargingSessionRead,
    ChargingSessionsResponse,
)
from app.services.charging_sessions_service import (
    ChargingSessionAlreadyCompletedError,
    ChargingSessionNotFoundError,
    ChargingSessionReservationNotFoundError,
    ChargingSessionStopNotAllowedError,
    ChargingSessionStationNotFoundError,
    complete_charging_session,
    get_active_charging_session,
    list_my_charging_sessions,
    mock_complete_charging_session,
    start_charging_session,
)

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)


@router.post(
    "",
    response_model=ChargingSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start charging session",
)
def start_my_charging_session(
    request: ChargingSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargingSessionRead:
    try:
        return start_charging_session(
            db,
            current_user=current_user,
            request=request,
        )
    except ChargingSessionStationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChargingSessionReservationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/me",
    response_model=ChargingSessionsResponse,
    status_code=status.HTTP_200_OK,
    summary="List my charging sessions",
)
def get_my_charging_sessions(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargingSessionsResponse:
    return ChargingSessionsResponse(
        sessions=list_my_charging_sessions(
            db,
            current_user=current_user,
            status=status_filter,
        )
    )


@router.get(
    "/active",
    response_model=ActiveChargingSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active charging session",
)
def get_my_active_charging_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActiveChargingSessionResponse:
    return ActiveChargingSessionResponse(
        session=get_active_charging_session(
            db,
            current_user=current_user,
        )
    )



@router.post(
    "/{session_id}/mock-complete",
    response_model=ChargingSessionRead,
    status_code=status.HTTP_200_OK,
    summary="Stop active mock charging session",
)
def mock_complete_my_charging_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargingSessionRead:
    try:
        return mock_complete_charging_session(
            db,
            current_user=current_user,
            session_id=session_id,
        )
    except ChargingSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChargingSessionAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ChargingSessionStopNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{session_id}/complete",
    response_model=ChargingSessionRead,
    status_code=status.HTTP_200_OK,
    summary="Complete charging session",
)
def complete_my_charging_session(
    session_id: uuid.UUID,
    request: ChargingSessionCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargingSessionRead:
    try:
        return complete_charging_session(
            db,
            current_user=current_user,
            session_id=session_id,
            request=request,
        )
    except ChargingSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChargingSessionAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
