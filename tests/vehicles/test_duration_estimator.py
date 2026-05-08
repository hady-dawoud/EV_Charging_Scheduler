from __future__ import annotations

from dataclasses import dataclass

from ev_core.vehicles.duration import estimate_duration_minutes, estimate_effective_power_kw


@dataclass(frozen=True)
class Station:
    connector_mix_total: str
    station_capacity_kw_assumed: float
    cp_count_total: int

    @property
    def average_port_power_kw(self) -> float:
        if self.cp_count_total <= 0:
            return 0.0
        return self.station_capacity_kw_assumed / self.cp_count_total


@dataclass(frozen=True)
class Request:
    vehicle_max_ac_kw: float | None = None
    vehicle_max_dc_kw: float | None = None


def test_no_vehicle_max_power_preserves_station_based_effective_power() -> None:
    station = Station(connector_mix_total="rapid", station_capacity_kw_assumed=300.0, cp_count_total=2)

    assert estimate_effective_power_kw(Request(), station) == 150.0


def test_station_average_power_keeps_legacy_lower_bound_without_vehicle_limits() -> None:
    station = Station(connector_mix_total="ac", station_capacity_kw_assumed=0.0, cp_count_total=0)

    assert estimate_effective_power_kw(Request(), station) == 7.0


def test_ac_station_uses_vehicle_ac_limit_when_lower_than_station_power() -> None:
    station = Station(connector_mix_total="ac", station_capacity_kw_assumed=44.0, cp_count_total=2)

    assert estimate_effective_power_kw(Request(vehicle_max_ac_kw=7.0), station) == 7.0


def test_rapid_station_uses_vehicle_dc_limit_when_lower_than_station_power() -> None:
    station = Station(connector_mix_total="rapid;ac", station_capacity_kw_assumed=300.0, cp_count_total=2)

    assert estimate_effective_power_kw(Request(vehicle_max_dc_kw=50.0), station) == 50.0


def test_station_power_lower_than_vehicle_limit_uses_station_power() -> None:
    station = Station(connector_mix_total="rapid", station_capacity_kw_assumed=100.0, cp_count_total=2)

    assert estimate_effective_power_kw(Request(vehicle_max_dc_kw=150.0), station) == 50.0


def test_duration_rounding_and_minimum_remain_time_step_based() -> None:
    assert estimate_duration_minutes(requested_energy_kwh=40.0, effective_power_kw=50.0, time_step_minutes=15) == 45
    assert estimate_duration_minutes(requested_energy_kwh=1.0, effective_power_kw=350.0, time_step_minutes=15) == 15
