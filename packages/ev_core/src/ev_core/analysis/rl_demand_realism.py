"""Helpers for RL demand-realism analysis and episode sizing."""

from __future__ import annotations

from calendar import isleap
from collections.abc import Mapping, Sequence
from typing import Any


UTILIZATION_BANDS = {
    "normal": (0.30, 0.60),
    "busy": (0.60, 0.80),
    "stress": (0.80, 1.00),
}


def build_utilization_bands(chargepoint_count: int) -> dict[str, dict[str, float]]:
    """Return active-car target bands derived from the available chargepoints."""

    cp_count = max(int(chargepoint_count), 0)
    bands: dict[str, dict[str, float]] = {}
    for name, (min_ratio, max_ratio) in UTILIZATION_BANDS.items():
        bands[name] = {
            "min_utilization": min_ratio,
            "max_utilization": max_ratio,
            "min_active_cars": round(cp_count * min_ratio, 3),
            "max_active_cars": round(cp_count * max_ratio, 3),
        }
    return bands


def suggest_episode_request_ranges(
    *,
    chargepoint_count: int,
    avg_duration_minutes: float,
    horizons_hours: Sequence[int] = (1, 3, 6, 24),
) -> dict[int, dict[str, dict[str, int]]]:
    """Estimate request-count ranges needed to hit target utilization bands."""

    avg_duration_hours = max(float(avg_duration_minutes), 1.0) / 60.0
    cp_count = max(int(chargepoint_count), 0)
    suggestions: dict[int, dict[str, dict[str, int]]] = {}
    for horizon_hours in horizons_hours:
        horizon = max(float(horizon_hours), 0.0)
        band_ranges: dict[str, dict[str, int]] = {}
        for name, (min_ratio, max_ratio) in UTILIZATION_BANDS.items():
            min_requests = int(round((cp_count * min_ratio / avg_duration_hours) * horizon))
            max_requests = int(round((cp_count * max_ratio / avg_duration_hours) * horizon))
            band_ranges[name] = {
                "min_requests": max(min_requests, 0),
                "max_requests": max(max_requests, max(min_requests, 0)),
            }
        suggestions[int(horizon_hours)] = band_ranges
    return suggestions


def build_demand_realism_summary(
    *,
    bundle: Any,
    vehicle_profiles: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute repo-backed demand realism metrics for RL planning."""

    stations = bundle.stations.copy()
    chargepoints = bundle.chargepoints.copy()
    zones = bundle.zones.copy()
    transformers = bundle.transformers.copy()
    params = dict(bundle.request_generator_params)

    station_count = int(stations["station_id"].nunique()) if "station_id" in stations else int(len(stations))
    chargepoint_count = int(chargepoints["cp_id"].nunique()) if "cp_id" in chargepoints else int(len(chargepoints))
    connector_count = chargepoint_count
    total_port_capacity_kw = round(float(chargepoints.get("assumed_port_kw", 0.0).fillna(0.0).sum()), 3)
    zone_count = int(zones["zone_id"].nunique()) if "zone_id" in zones else int(len(zones))
    transformer_count = int(transformers["transformer_id"].nunique()) if "transformer_id" in transformers else int(len(transformers))
    vehicle_profile_count = len(vehicle_profiles)

    yearly_counts = {
        str(year): int(count)
        for year, count in dict(params.get("request_counts_by_year", {})).items()
    }
    yearly_rates: dict[str, dict[str, float]] = {}
    arrivals_per_hour_values: list[float] = []
    for year_text, count in yearly_counts.items():
        year = int(year_text)
        days = 366 if isleap(year) else 365
        per_day = count / days if days else 0.0
        per_hour = per_day / 24.0
        arrivals_per_hour_values.append(per_hour)
        yearly_rates[year_text] = {
            "requests_total": count,
            "avg_requests_per_day": round(per_day, 3),
            "avg_requests_per_hour": round(per_hour, 3),
        }
    estimated_arrivals_per_hour = (
        sum(arrivals_per_hour_values) / len(arrivals_per_hour_values)
        if arrivals_per_hour_values
        else 0.0
    )

    avg_requested_energy_kwh = float(params.get("requested_energy_kwh_summary", {}).get("mean", 0.0) or 0.0)
    avg_duration_minutes = float(params.get("requested_duration_minutes_summary", {}).get("mean", 0.0) or 0.0)
    estimated_active_cars = estimated_arrivals_per_hour * max(avg_duration_minutes, 0.0) / 60.0

    utilization_bands = build_utilization_bands(chargepoint_count=chargepoint_count)
    scenario_request_ranges = suggest_episode_request_ranges(
        chargepoint_count=chargepoint_count,
        avg_duration_minutes=avg_duration_minutes,
    )

    return {
        "station_count": station_count,
        "chargepoint_count": chargepoint_count,
        "connector_count": connector_count,
        "total_port_capacity_kw": total_port_capacity_kw,
        "zone_count": zone_count,
        "transformer_count": transformer_count,
        "vehicle_profile_count": vehicle_profile_count,
        "historical_request_rate_summary": yearly_rates,
        "average_synthetic_live_requested_energy_kwh": round(avg_requested_energy_kwh, 3),
        "average_estimated_duration_minutes": round(avg_duration_minutes, 3),
        "estimated_arrivals_per_hour": round(estimated_arrivals_per_hour, 3),
        "estimated_active_cars": round(estimated_active_cars, 1),
        "utilization_bands": utilization_bands,
        "scenario_request_ranges": scenario_request_ranges,
    }
