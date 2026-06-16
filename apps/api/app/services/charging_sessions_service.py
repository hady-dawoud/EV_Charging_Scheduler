from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.charging_session import ChargingSession as ChargingSessionModel
from app.models.user import User
from app.repositories.charging_sessions_repository import (
    create_charging_session_record,
    get_active_charging_session_record_for_user,
    get_charging_session_record_for_user,
    list_charging_session_records_for_user,
    save_charging_session_record,
)
from app.repositories.reservations_repository import (
    get_reservation_record_by_id,
    get_reservation_record_for_user,
    save_reservation_record,
)
from app.repositories.stations_repository import get_station_record_by_id
from app.schemas.charging_sessions import (
    ChargingSessionCompleteRequest,
    ChargingSessionCreate,
    ChargingSessionRead,
)


class ChargingSessionNotFoundError(ValueError):
    pass


class ChargingSessionStationNotFoundError(ValueError):
    pass


class ChargingSessionReservationNotFoundError(ValueError):
    pass


class ChargingSessionAlreadyCompletedError(ValueError):
    pass


class ChargingSessionStopNotAllowedError(ValueError):
    pass


DEFAULT_STALE_ACTIVE_SESSION_MINUTES = 180
STALE_ACTIVE_SESSION_GRACE_MINUTES = 30


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def reconcile_stale_active_sessions_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> None:
    active_sessions = list_charging_session_records_for_user(
        db,
        user_id=user_id,
        status="active",
    )
    now = datetime.now(timezone.utc)

    for session in active_sessions:
        estimated_minutes = (
            session.reservation.estimated_duration_minutes
            if session.reservation is not None
            else None
        )
        max_minutes = (
            estimated_minutes + STALE_ACTIVE_SESSION_GRACE_MINUTES
            if estimated_minutes is not None
            else DEFAULT_STALE_ACTIVE_SESSION_MINUTES
        )
        started_at = _ensure_timezone(session.started_at)

        if now > started_at + timedelta(minutes=max_minutes):
            session.status = "stale_active"
            save_charging_session_record(db, session)


def build_charging_session_read(
    db: Session,
    session: ChargingSessionModel,
) -> ChargingSessionRead:
    station = get_station_record_by_id(db, session.station_id)
    station_name = station.station_name if station is not None else session.station_id

    return ChargingSessionRead(
        session_id=str(session.session_id),
        status=session.status,
        station_id=session.station_id,
        station_name=station_name,
        reservation_id=str(session.reservation_id) if session.reservation_id else None,
        client_request_id=session.client_request_id,
        request_id=session.request_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        energy_kwh=session.energy_kwh,
        cost_total=session.cost_total,
        connector_type=session.connector_type,
        charger_power_kw=session.charger_power_kw,
        created_at=session.created_at,
    )


def start_charging_session(
    db: Session,
    *,
    current_user: User,
    request: ChargingSessionCreate,
) -> ChargingSessionRead:
    station = get_station_record_by_id(db, request.station_id)

    if station is None:
        raise ChargingSessionStationNotFoundError("Station not found")

    reservation_uuid: uuid.UUID | None = None

    if request.reservation_id is not None:
        try:
            reservation_uuid = uuid.UUID(request.reservation_id)
        except ValueError as exc:
            raise ChargingSessionReservationNotFoundError("Invalid reservation ID") from exc

        reservation = get_reservation_record_for_user(
            db,
            reservation_id=reservation_uuid,
            user_id=current_user.id,
        )

        if reservation is None:
            raise ChargingSessionReservationNotFoundError("Reservation not found")

    started_at = (
        _ensure_timezone(request.started_at)
        if request.started_at is not None
        else datetime.now(timezone.utc)
    )

    session = ChargingSessionModel(
        user_id=current_user.id,
        station_id=request.station_id,
        reservation_id=reservation_uuid,
        client_request_id=request.client_request_id,
        request_id=request.request_id,
        status="active",
        started_at=started_at,
        connector_type=request.connector_type,
        charger_power_kw=request.charger_power_kw,
    )

    created = create_charging_session_record(db, session)

    return build_charging_session_read(db, created)


def list_my_charging_sessions(
    db: Session,
    *,
    current_user: User,
    status: str | None = None,
) -> list[ChargingSessionRead]:
    reconcile_stale_active_sessions_for_user(
        db,
        user_id=current_user.id,
    )

    sessions = list_charging_session_records_for_user(
        db,
        user_id=current_user.id,
        status=status,
    )

    return [
        build_charging_session_read(db, session)
        for session in sessions
    ]


def get_active_charging_session(
    db: Session,
    *,
    current_user: User,
) -> ChargingSessionRead | None:
    reconcile_stale_active_sessions_for_user(
        db,
        user_id=current_user.id,
    )

    session = get_active_charging_session_record_for_user(
        db,
        user_id=current_user.id,
    )

    if session is None:
        return None

    return build_charging_session_read(db, session)


def complete_charging_session(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
    request: ChargingSessionCompleteRequest,
) -> ChargingSessionRead:
    session = get_charging_session_record_for_user(
        db,
        session_id=session_id,
        user_id=current_user.id,
    )

    if session is None:
        raise ChargingSessionNotFoundError("Charging session not found")

    if session.status == "completed":
        raise ChargingSessionAlreadyCompletedError("Charging session is already completed")

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



def mock_complete_charging_session(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
) -> ChargingSessionRead:
    session = get_charging_session_record_for_user(
        db,
        session_id=session_id,
        user_id=current_user.id,
    )

    if session is None:
        raise ChargingSessionNotFoundError("Charging session not found")

    if session.status == "completed":
        raise ChargingSessionAlreadyCompletedError("Charging session is already completed")

    if session.status != "active":
        raise ChargingSessionStopNotAllowedError(
            f"Session cannot be stopped from status '{session.status}'"
        )

    ended_at = datetime.now(timezone.utc)
    started_at = _ensure_timezone(session.started_at)
    duration_hours = max(0, (ended_at - started_at).total_seconds() / 3600)

    charger_power_kw = session.charger_power_kw or 22.0
    energy_kwh = round(max(0.1, charger_power_kw * duration_hours), 3)
    cost_total = round(energy_kwh * 0.45, 2)

    return complete_charging_session(
        db,
        current_user=current_user,
        session_id=session_id,
        request=ChargingSessionCompleteRequest(
            ended_at=ended_at,
            energy_kwh=energy_kwh,
            cost_total=cost_total,
        ),
    )
