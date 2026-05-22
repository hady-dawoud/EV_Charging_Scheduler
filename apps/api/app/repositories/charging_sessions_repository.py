from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.charging_session import ChargingSession


def create_charging_session_record(
    db: Session,
    session: ChargingSession,
) -> ChargingSession:
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_charging_session_records_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    status: str | None = None,
) -> list[ChargingSession]:
    statement = select(ChargingSession).where(ChargingSession.user_id == user_id)

    if status:
        statement = statement.where(ChargingSession.status == status)

    statement = statement.order_by(ChargingSession.started_at.desc())

    return list(db.execute(statement).scalars().all())


def get_charging_session_record_for_user(
    db: Session,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ChargingSession | None:
    statement = select(ChargingSession).where(
        ChargingSession.session_id == session_id,
        ChargingSession.user_id == user_id,
    )

    return db.execute(statement).scalar_one_or_none()


def get_active_charging_session_record_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> ChargingSession | None:
    statement = (
        select(ChargingSession)
        .where(
            ChargingSession.user_id == user_id,
            ChargingSession.status == "active",
        )
        .order_by(ChargingSession.started_at.desc())
        .limit(1)
    )

    return db.execute(statement).scalar_one_or_none()


def save_charging_session_record(
    db: Session,
    session: ChargingSession,
) -> ChargingSession:
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
