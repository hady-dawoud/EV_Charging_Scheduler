from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.charger_events import (
    ChargerSessionCompleteEvent,
    ChargerSessionStartEvent,
)
from app.schemas.charging_sessions import ChargingSessionRead
from app.services.charger_events_service import (
    ChargerEventReservationCancelledError,
    ChargerEventReservationNotFoundError,
    ChargerEventSessionAlreadyCompletedError,
    ChargerEventSessionNotFoundError,
    complete_session_from_charger_event,
    start_session_from_charger_event,
)


router = APIRouter(
    prefix="/charger-events",
    tags=["charger-events"],
)


def verify_charger_event_secret(
    x_charger_event_secret: str = Header(default="", alias="X-Charger-Event-Secret"),
) -> None:
    settings = get_settings()

    if not settings.charger_event_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Charger event secret is not configured",
        )

    if x_charger_event_secret != settings.charger_event_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid charger event secret",
        )


@router.post(
    "/sessions/start",
    response_model=ChargingSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start charging session from charger event",
)
def start_session_event(
    request: ChargerSessionStartEvent,
    _: None = Depends(verify_charger_event_secret),
    db: Session = Depends(get_db),
) -> ChargingSessionRead:
    try:
        return start_session_from_charger_event(
            db,
            request=request,
        )
    except ChargerEventReservationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChargerEventReservationCancelledError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/sessions/{session_id}/complete",
    response_model=ChargingSessionRead,
    status_code=status.HTTP_200_OK,
    summary="Complete charging session from charger event",
)
def complete_session_event(
    session_id: uuid.UUID,
    request: ChargerSessionCompleteEvent,
    _: None = Depends(verify_charger_event_secret),
    db: Session = Depends(get_db),
) -> ChargingSessionRead:
    try:
        return complete_session_from_charger_event(
            db,
            session_id=session_id,
            request=request,
        )
    except ChargerEventSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChargerEventSessionAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
