from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.station import Station as StationModel
from app.repositories.stations_repository import (
    create_station_record,
    delete_station_record,
    get_station_record_by_id,
    list_station_records,
)
from app.schemas.stations import Station, StationCreate, StationUpdate


class StationAlreadyExistsError(ValueError):
    pass


def to_station_schema(station: StationModel) -> Station:
    return Station.model_validate(station)


def list_stations(
    db: Session,
    *,
    zone_id: str | None = None,
    available_only: bool = False,
    public_only: bool = True,
    include_excluded: bool = False,
) -> list[Station]:
    return [
        to_station_schema(station)
        for station in list_station_records(
            db,
            zone_id=zone_id,
            available_only=available_only,
            public_only=public_only,
            include_excluded=include_excluded,
        )
    ]


def get_station_by_id(db: Session, station_id: str) -> Station | None:
    station = get_station_record_by_id(db, station_id)

    if station is None:
        return None

    return to_station_schema(station)


def create_station(db: Session, station_in: StationCreate) -> Station:
    existing = get_station_record_by_id(db, station_in.station_id)

    if existing is not None:
        raise StationAlreadyExistsError("Station already exists")

    station = StationModel(**station_in.model_dump())
    created = create_station_record(db, station)

    return to_station_schema(created)


def update_station(
    db: Session,
    station_id: str,
    station_in: StationUpdate,
) -> Station | None:
    station = get_station_record_by_id(db, station_id)

    if station is None:
        return None

    updates = station_in.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(station, key, value)

    db.add(station)
    db.commit()
    db.refresh(station)

    return to_station_schema(station)


def delete_station(db: Session, station_id: str) -> bool:
    return delete_station_record(db, station_id)
