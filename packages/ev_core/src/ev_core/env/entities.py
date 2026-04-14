"""Core entities for the future multi-agent charging simulation environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ChargingConnector:
    """Connector metadata tracked by the environment."""

    connector_id: str
    max_power_kw: float


@dataclass(frozen=True)
class Station:
    """Station definition used by future request-allocation experiments."""

    station_id: str
    connectors: tuple[ChargingConnector, ...] = field(default_factory=tuple)
    transformer_limit_kw: float | None = None


@dataclass(frozen=True)
class VehicleRequest:
    """A single charging request aligned to a 15-minute planning horizon."""

    request_id: str
    vehicle_id: str
    arrival_at: datetime
    departure_by: datetime
    requested_energy_kwh: float
    max_accept_power_kw: float | None = None


@dataclass(frozen=True)
class GridContext:
    """External grid signals sampled on the shared 15-minute time base."""

    interval_start: datetime
    background_load_kw: float = 0.0
    tariff_per_kwh: float = 0.0
    pv_generation_kw: float = 0.0
