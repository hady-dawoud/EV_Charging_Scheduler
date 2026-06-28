"""Map EV-side request/candidate data into grid advisory proposals."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from ev_core.utils.timebase import TIME_STEP_MINUTES

from .contracts import GridSchedulePoint, GridScheduleProposal


def build_grid_schedule_proposal(
    *,
    request: Any,
    candidate: Any,
    episode_id: str | None = None,
    timebase_minutes: int = 30,
) -> GridScheduleProposal:
    """Build the DigitalTwin proposal for one station candidate."""

    requested_energy_kwh = max(float(getattr(request, "requested_energy_kwh", 0.0) or 0.0), 0.0)
    duration_minutes = max(int(getattr(candidate, "estimated_duration_minutes", TIME_STEP_MINUTES) or TIME_STEP_MINUTES), 1)
    duration_steps = max(int(math.ceil(duration_minutes / max(timebase_minutes, 1))), 1)
    charger_kw = _candidate_charger_kw(candidate, requested_energy_kwh=requested_energy_kwh, duration_minutes=duration_minutes)
    p_kw = min(charger_kw, requested_energy_kwh * 60.0 / max(duration_minutes, 1)) if requested_energy_kwh else charger_kw
    schedule = [
        GridSchedulePoint(time_index=index, p_kw=round(max(p_kw, 0.0), 6), q_kvar=0.0)
        for index in range(duration_steps)
    ]
    return GridScheduleProposal(
        request_id=str(getattr(request, "request_id", None) or getattr(request, "client_request_id", "unknown_request")),
        episode_id=episode_id or _metadata_value(request, "scenario_id"),
        station_id=str(getattr(candidate, "station_id")),
        area_id=_candidate_area_id(candidate),
        secondary_area_id=_candidate_metadata_value(candidate, "secondary_area_id") or _candidate_area_id(candidate),
        node_id=_candidate_metadata_value(candidate, "node_id") or _candidate_metadata_value(candidate, "assigned_node_id"),
        demand_point_id=_candidate_metadata_value(candidate, "demand_point_id"),
        asset_type=_candidate_metadata_value(candidate, "asset_type"),
        source_system=_candidate_metadata_value(candidate, "source_system"),
        start_timestamp=_request_start_timestamp(request),
        timebase_minutes=int(timebase_minutes),
        duration_steps=duration_steps,
        requested_energy_kwh=round(requested_energy_kwh, 6),
        charger_kw=round(charger_kw, 6),
        ev_schedule=schedule,
        evaluation_mode=str(_candidate_metadata_value(candidate, "evaluation_mode") or "replay"),
    )


def _candidate_area_id(candidate: Any) -> str:
    metadata = getattr(candidate, "metadata", {}) or {}
    for key in ("secondary_area_id", "digitaltwin_area_id", "area_id"):
        value = metadata.get(key)
        if value:
            return str(value)
    for key in ("digitaltwin_area_id", "area_id", "secondary_area_id"):
        value = metadata.get(key)
        if value:
            return str(value)
    transformer_id = getattr(candidate, "transformer_id", None)
    if transformer_id:
        return str(transformer_id)
    zone_id = getattr(candidate, "zone_id", None)
    if zone_id:
        return str(zone_id)
    return str(getattr(candidate, "station_id", "unknown_area"))


def _candidate_metadata_value(candidate: Any, key: str) -> str | None:
    metadata = getattr(candidate, "metadata", {}) or {}
    value = metadata.get(key)
    if value is None or str(value).strip() == "":
        value = getattr(candidate, key, None)
    return None if value is None or str(value).strip() == "" else str(value)


def _candidate_charger_kw(candidate: Any, *, requested_energy_kwh: float, duration_minutes: int) -> float:
    metadata = getattr(candidate, "metadata", {}) or {}
    for key in ("effective_power_kw", "selected_connector_power_kw", "charger_kw"):
        value = metadata.get(key)
        if value is not None:
            return max(_as_float(value), 0.0)
    if requested_energy_kwh <= 0.0:
        return 0.0
    return max(requested_energy_kwh * 60.0 / max(duration_minutes, 1), 1.0)


def _request_start_timestamp(request: Any) -> datetime:
    value = getattr(request, "arrival_ts", None) or getattr(request, "request_timestamp", None)
    if isinstance(value, datetime):
        return value
    return datetime(1970, 1, 1)


def _metadata_value(request: Any, key: str) -> str | None:
    metadata = getattr(request, "metadata", {}) or {}
    value = metadata.get(key)
    return None if value is None else str(value)


def _as_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


__all__ = ["build_grid_schedule_proposal"]
