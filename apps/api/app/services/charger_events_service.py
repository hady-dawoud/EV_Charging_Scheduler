from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.charging_session import ChargingSession as ChargingSessionModel
from app.repositories.charging_sessions_repository import (
    create_charging_session_record,
    get_active_charging_session_record_for_reservation,
    get_charging_session_record_by_id,
    save_charging_session_record,
)
from app.repositories.reservations_repository import (
    get_reservation_record_by_id,
    save_reservation_record,
)
from app.schemas.charger_events import (
    ChargerSessionCompleteEvent,
    ChargerSessionStartEvent,
)
from app.schemas.charging_sessions import ChargingSessionRead
from app.services.charging_sessions_service import build_charging_session_read


class ChargerEventReservationNotFoundError(ValueError):
    pass


class ChargerEventReservationCancelledError(ValueError):
    pass


class ChargerEventSessionNotFoundError(ValueError):
    pass


class ChargerEventSessionAlreadyCompletedError(ValueError):
    pass


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def start_session_from_charger_event(
    db: Session,
    *,
    request: ChargerSessionStartEvent,
) -> ChargingSessionRead:
    try:
        reservation_uuid = uuid.UUID(request.reservation_id)
    except ValueError as exc:
        raise ChargerEventReservationNotFoundError("Invalid reservation ID") from exc

    reservation = get_reservation_record_by_id(
        db,
        reservation_id=reservation_uuid,
    )

    if reservation is None:
        raise ChargerEventReservationNotFoundError("Reservation not found")

    if reservation.status == "cancelled":
        raise ChargerEventReservationCancelledError("Reservation is cancelled")

    existing_active = get_active_charging_session_record_for_reservation(
        db,
        reservation_id=reservation.reservation_id,
    )

    if existing_active is not None:
        return build_charging_session_read(db, existing_active)

    started_at = (
        _ensure_timezone(request.started_at)
        if request.started_at is not None
        else datetime.now(timezone.utc)
    )

    session = ChargingSessionModel(
        user_id=reservation.user_id,
        station_id=reservation.station_id,
        reservation_id=reservation.reservation_id,
        client_request_id=reservation.client_request_id,
        request_id=reservation.request_id,
        status="active",
        started_at=started_at,
        connector_type=request.connector_type or reservation.charger_label,
        charger_power_kw=request.charger_power_kw,
    )

    reservation.status = "active"

    created = create_charging_session_record(db, session)
    save_reservation_record(db, reservation)

    return build_charging_session_read(db, created)


def complete_session_from_charger_event(
    db: Session,
    *,
    session_id: uuid.UUID,
    request: ChargerSessionCompleteEvent,
) -> ChargingSessionRead:
    session = get_charging_session_record_by_id(
        db,
        session_id=session_id,
    )

    if session is None:
        raise ChargerEventSessionNotFoundError("Charging session not found")

    if session.status == "completed":
        raise ChargerEventSessionAlreadyCompletedError("Charging session is already completed")

    session.status = "completed"
    session.ended_at = (
        _ensure_timezone(request.ended_at)
        if request.ended_at is not None
        else datetime.now(timezone.utc)
    )
    session.energy_kwh = request.energy_kwh
    session.cost_total = request.cost_total

    saved = save_charging_session_record(db, session)

    if saved.reservation_id is not None:
        reservation = get_reservation_record_by_id(
            db,
            reservation_id=saved.reservation_id,
        )
        if reservation is not None:
            reservation.status = "completed"
            save_reservation_record(db, reservation)

    return build_charging_session_read(db, saved)
