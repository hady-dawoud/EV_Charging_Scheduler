from __future__ import annotations

from datetime import datetime, timedelta
import sys
import types

for module_name in ("numpy", "pandas"):
    module = types.ModuleType(module_name)
    module.DataFrame = object
    sys.modules.setdefault(module_name, module)

from ev_core.env.entities import SimulationRequest, Station
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


def simulation_request(
    *,
    latitude: float | None = 56.462,
    longitude: float | None = -2.97,
    zone_id: str = "zone-a",
) -> SimulationRequest:
    now = datetime(2024, 6, 10, 12, 0)
    return SimulationRequest(
        request_id="request-1",
        client_request_id="client-1",
        source_type="external_live",
        arrival_ts=now,
        latest_finish_ts=now + timedelta(hours=2),
        requested_energy_kwh=20.0,
        requested_duration_minutes=30,
        preference_mode="closest",
        charger_type_preference="Any",
        current_latitude=latitude,
        current_longitude=longitude,
        zone_id=zone_id,
    )


def station(*, zone_id: str = "zone-a", latitude: float = 56.46, longitude: float = -2.98) -> Station:
    return Station(
        station_id="station-1",
        station_name="Station 1",
        zone_id=zone_id,
        transformer_id="tx-1",
        latitude=latitude,
        longitude=longitude,
        cp_count_total=2,
        connector_mix_total="rapid;ac",
        station_capacity_kw_assumed=64.0,
    )


def test_simple_distance_provider_uses_existing_coordinate_formula() -> None:
    provider = SimpleDistanceRoutingProvider()

    estimate = provider.estimate_route(
        simulation_request(latitude=56.462, longitude=-2.97),
        station(latitude=56.46, longitude=-2.98),
    )

    expected = (((56.462 - 56.46) * 111.0) ** 2 + (((-2.97) - (-2.98)) * (111.0 * 0.56)) ** 2) ** 0.5
    assert estimate.distance_km == expected
    assert estimate.duration_minutes is None
    assert estimate.provider == "simple_distance"
    assert estimate.metadata is not None
    assert estimate.metadata["mode"] == "coordinate_distance"


def test_simple_distance_provider_uses_same_zone_fallback_without_coordinates() -> None:
    provider = SimpleDistanceRoutingProvider()

    estimate = provider.estimate_route(
        simulation_request(latitude=None, longitude=None, zone_id="zone-a"),
        station(zone_id="zone-a"),
    )

    assert estimate.distance_km == 0.5
    assert estimate.provider == "simple_distance"
    assert estimate.metadata is not None
    assert estimate.metadata["mode"] == "zone_fallback"


def test_simple_distance_provider_uses_different_zone_fallback_without_coordinates() -> None:
    provider = SimpleDistanceRoutingProvider()

    estimate = provider.estimate_route(
        simulation_request(latitude=None, longitude=None, zone_id="zone-a"),
        station(zone_id="zone-b"),
    )

    assert estimate.distance_km == 3.0
    assert estimate.provider == "simple_distance"


def test_simple_distance_provider_exposes_stable_name() -> None:
    provider = SimpleDistanceRoutingProvider()

    assert provider.name == "simple_distance"
