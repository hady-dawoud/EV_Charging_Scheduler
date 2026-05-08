from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import types

import pytest

for module_name in ("numpy", "pandas"):
    module = types.ModuleType(module_name)
    module.DataFrame = object
    sys.modules.setdefault(module_name, module)

from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import SimulationRequest, Station
from ev_core.routing.osmnx_provider import OSMnxRoutingProvider
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider, simple_distance_km


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


def test_osmnx_provider_missing_graph_falls_back_to_simple_distance(tmp_path: Path) -> None:
    graph_path = tmp_path / "missing.graphml"
    provider = OSMnxRoutingProvider(graph_path=graph_path)

    request = simulation_request()
    target = station()
    estimate = provider.estimate_route(request, target)

    assert estimate.provider == "simple_distance"
    assert estimate.distance_km == simple_distance_km(
        request.current_latitude,
        request.current_longitude,
        target.latitude,
        target.longitude,
    )
    assert estimate.metadata is not None
    assert estimate.metadata["fallback_used"] is True
    assert estimate.metadata["provider_requested"] == "osmnx"
    assert estimate.metadata["fallback_reason"] == "graph_missing"


def test_osmnx_provider_fail_closed_raises_when_graph_missing(tmp_path: Path) -> None:
    provider = OSMnxRoutingProvider(graph_path=tmp_path / "missing.graphml", fail_closed=True)

    with pytest.raises(RuntimeError, match="graph"):
        provider.estimate_route(simulation_request(), station())


def test_osmnx_provider_module_imports_without_osmnx_installed(tmp_path: Path) -> None:
    provider = OSMnxRoutingProvider(graph_path=tmp_path / "missing.graphml")

    assert provider.name == "osmnx"
    assert isinstance(provider.fallback_provider, SimpleDistanceRoutingProvider)


def test_osmnx_provider_uses_fake_graph_route_when_backends_are_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    graph_path = tmp_path / "dundee.graphml"
    graph_path.write_text("fake graph placeholder", encoding="utf-8")
    provider = OSMnxRoutingProvider(graph_path=graph_path, speed_kph=30.0)

    class FakeOsmnxDistance:
        @staticmethod
        def nearest_nodes(graph, x, y):
            if (x, y) == (-2.97, 56.462):
                return "origin-node"
            if (x, y) == (-2.98, 56.46):
                return "destination-node"
            raise AssertionError(f"unexpected coordinates {(x, y)}")

    class FakeOsmnx:
        distance = FakeOsmnxDistance()

        @staticmethod
        def load_graphml(path):
            assert Path(path) == graph_path
            return {"graph": "fake"}

    class FakeNetworkX:
        @staticmethod
        def shortest_path(graph, origin, destination, weight):
            assert graph == {"graph": "fake"}
            assert origin == "origin-node"
            assert destination == "destination-node"
            assert weight == "length"
            return ["origin-node", "mid-node", "destination-node"]

        @staticmethod
        def path_weight(graph, path, weight):
            assert weight in {"length", "travel_time"}
            if weight == "length":
                return 2450.0
            if weight == "travel_time":
                return 420.0
            raise AssertionError("unexpected weight")

    monkeypatch.setattr(provider, "_import_backends", lambda: (FakeOsmnx, FakeNetworkX))

    estimate = provider.estimate_route(simulation_request(), station())

    assert estimate.provider == "osmnx"
    assert round(estimate.distance_km, 3) == 2.45
    assert estimate.duration_minutes == 7.0
    assert estimate.metadata is not None
    assert estimate.metadata["origin_node"] == "origin-node"
    assert estimate.metadata["destination_node"] == "destination-node"
    assert estimate.metadata["fallback_used"] is False
    assert Path(estimate.metadata["graph_path"]) == graph_path


def test_osmnx_provider_uses_speed_fallback_when_travel_time_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_path = tmp_path / "dundee.graphml"
    graph_path.write_text("fake graph placeholder", encoding="utf-8")
    provider = OSMnxRoutingProvider(graph_path=graph_path, speed_kph=30.0)

    class FakeOsmnxDistance:
        @staticmethod
        def nearest_nodes(graph, x, y):
            return "node-a" if (x, y) == (-2.97, 56.462) else "node-b"

    class FakeOsmnx:
        distance = FakeOsmnxDistance()

        @staticmethod
        def load_graphml(path):
            return {"graph": "fake"}

    class FakeNetworkX:
        @staticmethod
        def shortest_path(graph, origin, destination, weight):
            return ["node-a", "node-b"]

        @staticmethod
        def path_weight(graph, path, weight):
            if weight == "length":
                return 3000.0
            raise KeyError(weight)

    monkeypatch.setattr(provider, "_import_backends", lambda: (FakeOsmnx, FakeNetworkX))

    estimate = provider.estimate_route(simulation_request(), station())

    assert estimate.provider == "osmnx"
    assert estimate.duration_minutes == 6.0
    assert estimate.metadata is not None
    assert estimate.metadata["duration_source"] == "speed_kph_fallback"


def test_dundee_env_can_use_osmnx_provider_and_fallback_safely(tmp_path: Path) -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    env.routing_provider = OSMnxRoutingProvider(graph_path=tmp_path / "missing.graphml")

    request = simulation_request()
    target = station()
    distance = env._distance_to_station_km(request, target)

    assert distance == simple_distance_km(
        request.current_latitude,
        request.current_longitude,
        target.latitude,
        target.longitude,
    )
