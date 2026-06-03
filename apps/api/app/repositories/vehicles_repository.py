from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vehicle import UserVehicle


def get_vehicle_by_user_id(
    db: Session,
    user_id: uuid.UUID,
) -> UserVehicle | None:
    statement = select(UserVehicle).where(UserVehicle.user_id == user_id)
    return db.execute(statement).scalar_one_or_none()


def create_vehicle(
    db: Session,
    *,
    user_id: uuid.UUID,
    make: str,
    model: str,
    battery_capacity_kwh: float,
    current_soc: float,
    range_km: float,
) -> UserVehicle:
    vehicle = UserVehicle(
        user_id=user_id,
        make=make,
        model=model,
        battery_capacity_kwh=battery_capacity_kwh,
        current_soc=current_soc,
        range_km=range_km,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(
    db: Session,
    *,
    vehicle: UserVehicle,
    make: str,
    model: str,
    battery_capacity_kwh: float,
    current_soc: float,
    range_km: float,
) -> UserVehicle:
    vehicle.make = make
    vehicle.model = model
    vehicle.battery_capacity_kwh = battery_capacity_kwh
    vehicle.current_soc = current_soc
    vehicle.range_km = range_km

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle
