from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vehicle import UserVehicle
from app.repositories.vehicles_repository import (
    create_vehicle,
    get_vehicle_by_user_id,
    update_vehicle,
)
from app.schemas.vehicles import UserVehicleRead, UserVehicleUpsertRequest


DEFAULT_VEHICLE = {
    "make": "Tesla",
    "model": "Model 3 LR",
    "battery_capacity_kwh": 82.0,
    "current_soc": 45.0,
    "range_km": 225.0,
}


def build_vehicle_read(vehicle: UserVehicle) -> UserVehicleRead:
    return UserVehicleRead(
        id=str(vehicle.id),
        make=vehicle.make,
        model=vehicle.model,
        battery_capacity_kwh=vehicle.battery_capacity_kwh,
        current_soc=vehicle.current_soc,
        range_km=vehicle.range_km,
    )


def get_or_create_vehicle_for_user(
    db: Session,
    *,
    current_user: User,
) -> UserVehicleRead:
    vehicle = get_vehicle_by_user_id(db, current_user.id)

    if vehicle is None:
        vehicle = create_vehicle(
            db,
            user_id=current_user.id,
            **DEFAULT_VEHICLE,
        )

    return build_vehicle_read(vehicle)


def upsert_vehicle_for_user(
    db: Session,
    *,
    current_user: User,
    request: UserVehicleUpsertRequest,
) -> UserVehicleRead:
    vehicle = get_vehicle_by_user_id(db, current_user.id)

    if vehicle is None:
        vehicle = create_vehicle(
            db,
            user_id=current_user.id,
            make=request.make,
            model=request.model,
            battery_capacity_kwh=request.battery_capacity_kwh,
            current_soc=request.current_soc,
            range_km=request.range_km,
        )
    else:
        vehicle = update_vehicle(
            db,
            vehicle=vehicle,
            make=request.make,
            model=request.model,
            battery_capacity_kwh=request.battery_capacity_kwh,
            current_soc=request.current_soc,
            range_km=request.range_km,
        )

    return build_vehicle_read(vehicle)
