"""Contracts for feeder-aligned station-selection RL."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class FeederAction:
    """One DigitalTwin public-EV node that can be selected by the RL policy."""

    station_id: str
    secondary_area_id: str
    demand_point_id: str
    node_id: str
    p_base_kw: float = 0.0
    public_ev_capacity_kw: float = 22.0
    charger_kw: float = 22.0
    connector_type: str = "ac"
    latitude: float | None = None
    longitude: float | None = None
    x: float | None = None
    y: float | None = None
    truth_status: str = "feeder_aligned"
    source_system: str = "digitaltwin_phase39"
    metadata: dict[str, str | float | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class FeederRequest:
    """One simulated customer request scoped to a DigitalTwin feeder area."""

    request_id: str
    secondary_area_id: str
    arrival_timestamp: datetime
    latest_finish_timestamp: datetime
    requested_energy_kwh: float
    battery_kwh: float
    current_soc: float
    target_soc: float
    charger_type_preference: str
    max_ac_kw: float
    max_dc_kw: float
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    origin_x: float | None = None
    origin_y: float | None = None
    source_mix_metadata: dict[str, str | float | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class FeederEpisodeScenario:
    """One feeder-aligned RL episode definition."""

    scenario_id: str
    seed: int
    split: str
    secondary_area_id: str
    start_ts: datetime
    duration_hours: int
    request_count: int
    request_prior_sources: tuple[str, ...] = ("dundee", "acn", "digitaltwin")
    grid_evaluation_mode: str = "replay"

    @property
    def end_ts(self) -> datetime:
        return self.start_ts + timedelta(hours=self.duration_hours)


__all__ = ["FeederAction", "FeederEpisodeScenario", "FeederRequest"]
