"""Vehicle-aware charging duration estimation helpers."""

from __future__ import annotations

from typing import Any


RAPID_CONNECTOR_TOKENS = {"rapid", "ultra_rapid", "ultrarapid", "dc"}


def estimate_connector_effective_power_kw(request: Any, connector: Any) -> float:
    """Estimate effective power for a specific connector and optional vehicle caps."""

    connector_power_kw = max(float(getattr(connector, "max_power_kw", 0.0)), 1.0)
    connector_type = str(getattr(connector, "connector_type", "unknown")).strip().lower()
    is_dc_like = connector_type in RAPID_CONNECTOR_TOKENS

    if is_dc_like and getattr(request, "vehicle_max_dc_kw", None) is not None:
        return max(min(connector_power_kw, float(request.vehicle_max_dc_kw)), 1.0)
    if connector_type == "ac" and getattr(request, "vehicle_max_ac_kw", None) is not None:
        return max(min(connector_power_kw, float(request.vehicle_max_ac_kw)), 1.0)
    return connector_power_kw


def estimate_effective_power_kw(request: Any, station: Any) -> float:
    """Estimate effective charging power using station power and optional vehicle limits."""

    station_power_kw = max(float(station.average_port_power_kw), 7.0)
    connector_tokens = {item.strip().lower() for item in str(station.connector_mix_total).split(";") if item.strip()}
    is_dc_like = bool(connector_tokens & RAPID_CONNECTOR_TOKENS)

    if is_dc_like and getattr(request, "vehicle_max_dc_kw", None) is not None:
        return max(min(station_power_kw, float(request.vehicle_max_dc_kw)), 1.0)
    if not is_dc_like and getattr(request, "vehicle_max_ac_kw", None) is not None:
        return max(min(station_power_kw, float(request.vehicle_max_ac_kw)), 1.0)
    return station_power_kw


def estimate_duration_minutes(
    *,
    requested_energy_kwh: float,
    effective_power_kw: float,
    time_step_minutes: int,
) -> int:
    """Estimate charging duration with the existing nearest-step rounding rule.

    TODO: replace this linear estimate with charging-curve-aware duration once
    vehicle profiles include tapering/SOC curve parameters.
    """

    return max(
        int(round((requested_energy_kwh / max(effective_power_kw, 1.0)) * 60.0 / time_step_minutes) * time_step_minutes),
        time_step_minutes,
    )


__all__ = [
    "estimate_connector_effective_power_kw",
    "estimate_duration_minutes",
    "estimate_effective_power_kw",
]
