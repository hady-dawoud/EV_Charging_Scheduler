"""Core Dundee simulator entities used by the EV-side runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ChargingConnector:
    """Connector metadata tracked by the environment."""

    connector_id: str
    max_power_kw: float
    connector_type: str = "unknown"
    cp_id: str | None = None


@dataclass(frozen=True)
class Station:
    """Static Dundee station definition used by the runtime and dashboard."""

    station_id: str
    station_name: str
    zone_id: str
    transformer_id: str
    latitude: float
    longitude: float
    cp_count_total: int
    connector_mix_total: str
    station_capacity_kw_assumed: float
    connectors: tuple[ChargingConnector, ...] = field(default_factory=tuple)
    is_public: bool = True
    is_fleet_only: bool = False
    requires_membership: bool = False
    needs_followup: bool = False
    exclude_from_recommendations: bool = False
    access_notes: str | None = None

    @property
    def average_port_power_kw(self) -> float:
        """Average port power proxy used by the simple simulator policies."""

        if self.cp_count_total <= 0:
            return 0.0
        return float(self.station_capacity_kw_assumed) / float(self.cp_count_total)


@dataclass(frozen=True)
class Transformer:
    """Static synthetic transformer definition for simulator V1."""

    transformer_id: str
    transformer_name: str
    zone_id: str
    capacity_kw: float
    attached_station_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class SimulationRequest:
    """Request tracked by the Dundee runtime on the 15-minute time base."""

    request_id: str
    client_request_id: str | None
    source_type: str
    arrival_ts: datetime
    latest_finish_ts: datetime
    requested_energy_kwh: float
    requested_duration_minutes: int
    preference_mode: str
    charger_type_preference: str
    current_latitude: float | None = None
    current_longitude: float | None = None
    zone_id: str | None = None
    assigned_station_id: str | None = None
    assigned_transformer_id: str | None = None
    source_session_id: str | None = None
    target_soc: float | None = None
    current_soc: float | None = None
    battery_kwh: float | None = None
    vehicle_profile_id: str | None = None
    vehicle_max_ac_kw: float | None = None
    vehicle_max_dc_kw: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    queue_entered_ts: datetime | None = None
    started_at: datetime | None = None
    expected_completion_ts: datetime | None = None
    remaining_minutes: int | None = None


@dataclass
class ActiveChargingSession:
    """Session occupying a station port inside the simulator."""

    request_id: str
    station_id: str
    transformer_id: str
    started_at: datetime
    expected_completion_ts: datetime
    assigned_power_kw: float
    estimated_cost_gbp: float
    connector_id: str | None = None
    connector_type: str | None = None


@dataclass
class GridContext:
    """External grid signals sampled on the shared 15-minute time base."""

    interval_start: datetime
    background_load_kw: float = 0.0
    tariff_per_kwh: float = 0.0
    pv_generation_kw: float = 0.0


@dataclass
class StationRuntimeState:
    """Mutable queue and occupancy state for a Dundee station."""

    station: Station
    active_session_ids: list[str] = field(default_factory=list)
    queue_request_ids: list[str] = field(default_factory=list)


__all__ = [
    "ActiveChargingSession",
    "ChargingConnector",
    "GridContext",
    "SimulationRequest",
    "Station",
    "StationRuntimeState",
    "Transformer",
]
