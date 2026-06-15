from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.reservation import Reservation as ReservationModel
from app.models.user import User
from app.repositories.charging_sessions_repository import get_active_charging_session_record_for_user
from app.repositories.reservations_repository import (
    create_reservation_record,
    get_reservation_record_for_user,
    list_reservation_records_for_user,
    save_reservation_record,
)
from app.repositories.stations_repository import get_station_record_by_id
from app.services.charger_events_service import (
    ChargerEventReservationCancelledError,
    ChargerEventReservationNotFoundError,
    start_session_from_charger_event,
)
from app.services.ocpp_mock_service import authorize_and_start_transaction
from app.schemas.charger_events import ChargerSessionStartEvent
from app.schemas.charging_sessions import ChargingSessionRead
from app.schemas.reservations import (
    ReservationCancelResponse,
    ReservationCreate,
    ReservationRead,
)


class ReservationNotFoundError(ValueError):
    pass


class ReservationStationNotFoundError(ValueError):
    pass


class ReservationAlreadyCancelledError(ValueError):
    pass


class ReservationStartNotAllowedError(ValueError):
    pass


class ReservationActiveSessionError(ValueError):
    pass


class ReservationOpenReservationError(ValueError):
    pass


RESERVATION_EXPIRY_GRACE_MINUTES = 10


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def reconcile_expired_reservations(
    db: Session,
    reservations: list[ReservationModel],
) -> list[ReservationModel]:
    now = datetime.now(timezone.utc)

    for reservation in reservations:
        reserved_until = _ensure_timezone(reservation.reserved_until)

        if (
            reservation.status == "confirmed"
            and now > reserved_until + timedelta(minutes=RESERVATION_EXPIRY_GRACE_MINUTES)
        ):
            reservation.status = "expired"
            save_reservation_record(db, reservation)

    return reservations


def build_reservation_read(
    db: Session,
    reservation: ReservationModel,
) -> ReservationRead:
    station = get_station_record_by_id(db, reservation.station_id)
    station_name = station.station_name if station is not None else reservation.station_id

    return ReservationRead(
        reservation_id=str(reservation.reservation_id),
        status=reservation.status,
        station_id=reservation.station_id,
        station_name=station_name,
        client_request_id=reservation.client_request_id,
        request_id=reservation.request_id,
        recommendation_rank=reservation.recommendation_rank,
        reserved_start_at=reservation.reserved_start_at,
        reserved_until=reservation.reserved_until,
        cancelled_at=reservation.cancelled_at,
        estimated_cost_gbp=reservation.estimated_cost_gbp,
        estimated_duration_minutes=reservation.estimated_duration_minutes,
        charger_label=reservation.charger_label,
        distance_km=reservation.distance_km,
        score=reservation.score,
        created_at=reservation.created_at,
    )


def create_reservation(
    db: Session,
    *,
    current_user: User,
    request: ReservationCreate,
) -> ReservationRead:
    active_session = get_active_charging_session_record_for_user(
        db,
        user_id=current_user.id,
    )

    if active_session is not None:
        raise ReservationActiveSessionError(
            "Cannot create a reservation while a charging session is active"
        )

    existing_reservations = list_reservation_records_for_user(
        db,
        user_id=current_user.id,
    )
    existing_reservations = reconcile_expired_reservations(db, existing_reservations)

    open_reservation = next(
        (
            reservation
            for reservation in existing_reservations
            if reservation.status in {"confirmed", "active"}
            and reservation.cancelled_at is None
        ),
        None,
    )

    if open_reservation is not None:
        raise ReservationOpenReservationError(
            "Cannot create a reservation while another reservation is still open"
        )

    station = get_station_record_by_id(db, request.station_id)

    if station is None:
        raise ReservationStationNotFoundError("Station not found")

    reserved_start_at = _ensure_timezone(request.reserved_start_at)
    reserved_until = (
        _ensure_timezone(request.reserved_until)
        if request.reserved_until is not None
        else reserved_start_at + timedelta(minutes=15)
    )

    reservation = ReservationModel(
        user_id=current_user.id,
        station_id=request.station_id,
        client_request_id=request.client_request_id,
        request_id=request.request_id,
        recommendation_rank=request.recommendation_rank,
        status="confirmed",
        reserved_start_at=reserved_start_at,
        reserved_until=reserved_until,
        estimated_cost_gbp=request.estimated_cost_gbp,
        estimated_duration_minutes=request.estimated_duration_minutes,
        charger_label=request.charger_label,
        distance_km=request.distance_km,
        score=request.score,
    )

    created = create_reservation_record(db, reservation)

    return build_reservation_read(db, created)


def list_my_reservations(
    db: Session,
    *,
    current_user: User,
) -> list[ReservationRead]:
    reservations = list_reservation_records_for_user(
        db,
        user_id=current_user.id,
    )

    reservations = reconcile_expired_reservations(db, reservations)

    return [
        build_reservation_read(db, reservation)
        for reservation in reservations
    ]


def cancel_reservation(
    db: Session,
    *,
    current_user: User,
    reservation_id: uuid.UUID,
) -> ReservationCancelResponse:
    reservation = get_reservation_record_for_user(
        db,
        reservation_id=reservation_id,
        user_id=current_user.id,
    )

    if reservation is None:
        raise ReservationNotFoundError("Reservation not found")

    if reservation.status == "cancelled":
        raise ReservationAlreadyCancelledError("Reservation is already cancelled")

    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now(timezone.utc)

    saved = save_reservation_record(db, reservation)

    return ReservationCancelResponse(
        reservation_id=str(saved.reservation_id),
        status=saved.status,
    )



def confirm_reservation_start(
    db: Session,
    *,
    current_user: User,
    reservation_id: uuid.UUID,
) -> ChargingSessionRead:
    reservation = get_reservation_record_for_user(
        db,
        reservation_id=reservation_id,
        user_id=current_user.id,
    )

    if reservation is None:
        raise ReservationNotFoundError("Reservation not found")

    if reservation.status == "cancelled":
        raise ReservationStartNotAllowedError("Reservation is cancelled")

    if reservation.status == "expired":
        raise ReservationStartNotAllowedError("Reservation is expired")

    if reservation.status == "completed":
        raise ReservationStartNotAllowedError("Reservation is already completed")

    if reservation.status == "confirmed":
        reserved_until = _ensure_timezone(reservation.reserved_until)
        now = datetime.now(timezone.utc)

        if now > reserved_until + timedelta(minutes=RESERVATION_EXPIRY_GRACE_MINUTES):
            reservation.status = "expired"
            save_reservation_record(db, reservation)
            raise ReservationStartNotAllowedError("Reservation is expired")

    if reservation.status not in {"confirmed", "active"}:
        raise ReservationStartNotAllowedError(
            f"Reservation cannot be started from status '{reservation.status}'"
        )

    active_session = get_active_charging_session_record_for_user(
        db,
        user_id=current_user.id,
    )

    if (
        active_session is not None
        and active_session.reservation_id != reservation.reservation_id
    ):
        raise ReservationStartNotAllowedError(
            "Cannot start another reservation while a charging session is active"
        )

    mock_ocpp = authorize_and_start_transaction(
        user_id=str(current_user.id),
        reservation_id=str(reservation.reservation_id),
        station_id=reservation.station_id,
        charger_label=reservation.charger_label,
    )

    if mock_ocpp.status != "accepted":
        raise ReservationStartNotAllowedError("Mock OCPP rejected the start request")

    try:
        return start_session_from_charger_event(
            db,
            request=ChargerSessionStartEvent(
                reservation_id=str(reservation.reservation_id),
                connector_type=mock_ocpp.connector_type or reservation.charger_label,
                charger_power_kw=mock_ocpp.charger_power_kw,
            ),
        )
    except (
        ChargerEventReservationNotFoundError,
        ChargerEventReservationCancelledError,
    ) as exc:
        raise ReservationStartNotAllowedError(str(exc)) from exc
