"""Candidate construction for Dundee station recommendations."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from typing import Any

from ev_core.utils.timebase import TIME_STEP_MINUTES, minutes_between
from ev_core.vehicles.duration import estimate_duration_minutes, estimate_effective_power_kw

from .eligibility import StationEligibilityFilter
from .ranker import CandidateContext


class CandidateBuilder:
    """Build raw recommendation candidate contexts from runtime station state."""

    def build(
        self,
        *,
        request: Any,
        stations: Iterable[Any],
        stations_runtime: Mapping[str, Any],
        current_time: datetime,
        only_station_id: str | None = None,
        distance_to_station_km: Callable[[Any, Any], float],
        estimate_station_wait_minutes: Callable[[str], int],
        current_price_per_kwh: Callable[[], float],
        current_transformer_headroom: Callable[[str], float],
        is_charger_compatible: Callable[[str, str], bool],
        station_eligibility_filter: StationEligibilityFilter | None = None,
        station_effective_power_kw: Callable[[Any, Any], float] | None = None,
        compatible_available_port_count: Callable[[Any, Any], int] | None = None,
    ) -> list[CandidateContext]:
        contexts: list[CandidateContext] = []
        eligibility_filter = station_eligibility_filter or StationEligibilityFilter()
        remaining_window_minutes = max(minutes_between(current_time, request.latest_finish_ts), TIME_STEP_MINUTES)
        for station in stations:
            if only_station_id is not None and station.station_id != only_station_id:
                continue
            if not eligibility_filter.is_eligible(station, request).eligible:
                continue
            if compatible_available_port_count is not None:
                compatible_port_count = int(compatible_available_port_count(request, station))
                compatible = compatible_port_count > 0
            else:
                compatible_port_count = None
                compatible = is_charger_compatible(request.charger_type_preference, station.connector_mix_total)
            effective_power = (
                station_effective_power_kw(request, station)
                if station_effective_power_kw is not None
                else estimate_effective_power_kw(request, station)
            )
            estimated_duration = estimate_duration_minutes(
                requested_energy_kwh=request.requested_energy_kwh,
                effective_power_kw=effective_power,
                time_step_minutes=TIME_STEP_MINUTES,
            )
            estimated_wait = estimate_station_wait_minutes(station.station_id)
            if compatible and estimated_duration + estimated_wait <= remaining_window_minutes:
                station_runtime = stations_runtime[station.station_id]
                contexts.append(
                    CandidateContext(
                        station_id=station.station_id,
                        station_name=station.station_name,
                        zone_id=station.zone_id,
                        transformer_id=station.transformer_id,
                        distance_km=distance_to_station_km(request, station),
                        estimated_wait_minutes=estimated_wait,
                        estimated_duration_minutes=estimated_duration,
                        estimated_cost_gbp=request.requested_energy_kwh * current_price_per_kwh(),
                        transformer_headroom_kw=current_transformer_headroom(station.transformer_id),
                        current_queue=len(station_runtime.queue_request_ids),
                        utilization=len(station_runtime.active_session_ids) / max(station.cp_count_total, 1),
                        charger_compatible=compatible,
                        metadata={"connector_mix_total": station.connector_mix_total},
                    )
                )
        return contexts


__all__ = ["CandidateBuilder"]
