from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reservation import Reservation


def create_reservation_record(
    db: Session,
    reservation: Reservation,
) -> Reservation:
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def list_reservation_records_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> list[Reservation]:
    statement = (
        select(Reservation)
        .where(Reservation.user_id == user_id)
        .order_by(Reservation.created_at.desc())
    )

    return list(db.execute(statement).scalars().all())


def get_reservation_record_for_user(
    db: Session,
    *,
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Reservation | None:
    statement = select(Reservation).where(
        Reservation.reservation_id == reservation_id,
        Reservation.user_id == user_id,
    )

    return db.execute(statement).scalar_one_or_none()


def save_reservation_record(
    db: Session,
    reservation: Reservation,
) -> Reservation:
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def get_reservation_record_by_id(
    db: Session,
    *,
    reservation_id: uuid.UUID,
) -> Reservation | None:
    statement = select(Reservation).where(
        Reservation.reservation_id == reservation_id,
    )

    return db.execute(statement).scalar_one_or_none()
