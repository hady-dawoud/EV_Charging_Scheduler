"""Default vehicle profile catalog for recommendation duration estimates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleProfile:
    vehicle_profile_id: str
    vehicle_name: str
    battery_kwh: float
    ac_max_kw: float
    dc_max_kw: float
    efficiency_kwh_per_km: float | None = None
    market_share: float = 1.0


DEFAULT_VEHICLE_PROFILES = {
    "small_ev": VehicleProfile(
        vehicle_profile_id="small_ev",
        vehicle_name="Small EV",
        battery_kwh=40.0,
        ac_max_kw=7.0,
        dc_max_kw=50.0,
    ),
    "mid_ev": VehicleProfile(
        vehicle_profile_id="mid_ev",
        vehicle_name="Mid-size EV",
        battery_kwh=60.0,
        ac_max_kw=11.0,
        dc_max_kw=100.0,
    ),
    "large_ev": VehicleProfile(
        vehicle_profile_id="large_ev",
        vehicle_name="Large EV",
        battery_kwh=82.0,
        ac_max_kw=11.0,
        dc_max_kw=150.0,
    ),
    "van_ev": VehicleProfile(
        vehicle_profile_id="van_ev",
        vehicle_name="Electric Van",
        battery_kwh=100.0,
        ac_max_kw=22.0,
        dc_max_kw=120.0,
    ),
}


def get_default_vehicle_profiles() -> dict[str, VehicleProfile]:
    return dict(DEFAULT_VEHICLE_PROFILES)


def get_vehicle_profile(profile_id: str) -> VehicleProfile:
    return DEFAULT_VEHICLE_PROFILES[profile_id]


__all__ = ["DEFAULT_VEHICLE_PROFILES", "VehicleProfile", "get_default_vehicle_profiles", "get_vehicle_profile"]
