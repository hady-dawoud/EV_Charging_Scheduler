"""Vehicle profile and charging duration helpers."""

from .duration import estimate_duration_minutes, estimate_effective_power_kw
from .profiles import DEFAULT_VEHICLE_PROFILES, VehicleProfile, get_default_vehicle_profiles, get_vehicle_profile

__all__ = [
    "DEFAULT_VEHICLE_PROFILES",
    "VehicleProfile",
    "estimate_duration_minutes",
    "estimate_effective_power_kw",
    "get_default_vehicle_profiles",
    "get_vehicle_profile",
]
