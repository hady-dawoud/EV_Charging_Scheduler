from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.station import Station


def list_station_records(
    db: Session,
    *,
    zone_id: str | None = None,
    available_only: bool = False,
    public_only: bool = True,
    include_excluded: bool = False,
) -> list[Station]:
    statement = select(Station)

    if zone_id:
        statement = statement.where(Station.zone_id == zone_id)

    if public_only:
        statement = statement.where(Station.is_public.is_(True))

    if not include_excluded:
        statement = statement.where(Station.exclude_from_recommendations.is_(False))

    if available_only:
        statement = statement.where(Station.cp_count_total > 0)

    statement = statement.order_by(Station.station_name.asc())

    return list(db.execute(statement).scalars().all())


def get_station_record_by_id(db: Session, station_id: str) -> Station | None:
    return db.get(Station, station_id)


def create_station_record(db: Session, station: Station) -> Station:
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


def upsert_station_record(db: Session, station: Station) -> Station:
    existing = db.get(Station, station.station_id)

    if existing is None:
        return create_station_record(db, station)

    for key, value in station.__dict__.items():
        if key.startswith("_") or key in {"station_id", "created_at"}:
            continue
        setattr(existing, key, value)

    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def delete_station_record(db: Session, station_id: str) -> bool:
    station = db.get(Station, station_id)

    if station is None:
        return False

    db.delete(station)
    db.commit()
    return True
