from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.reservation import Reservation as ReservationModel
from app.models.user import User
from app.repositories.reservations_repository import (
    create_reservation_record,
    get_reservation_record_for_user,
    list_reservation_records_for_user,
    save_reservation_record,
)
from app.repositories.stations_repository import get_station_record_by_id
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


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


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
