from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

for module_name in ("numpy", "pandas"):
    module = types.ModuleType(module_name)
    module.DataFrame = object
    sys.modules.setdefault(module_name, module)

from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import ChargingConnector, SimulationRequest, Station, StationRuntimeState


def build_station(
    station_id: str,
    *,
    connectors: tuple[ChargingConnector, ...],
    connector_mix_total: str = "ac;rapid;ultra_rapid",
) -> Station:
    return Station(
        station_id=station_id,
        station_name=station_id.replace("-", " ").title(),
        zone_id="zone-a",
        transformer_id="tx-1",
        latitude=56.46,
        longitude=-2.97,
        cp_count_total=max(len(connectors), 1),
        connector_mix_total=connector_mix_total,
        station_capacity_kw_assumed=sum(connector.max_power_kw for connector in connectors) or 22.0,
        connectors=connectors,
    )


def build_request(
    *,
    charger_type_preference: str = "Any",
    vehicle_max_ac_kw: float | None = None,
    vehicle_max_dc_kw: float | None = None,
) -> SimulationRequest:
    now = datetime(2024, 6, 10, 12, 0)
    return SimulationRequest(
        request_id=f"request-{charger_type_preference}",
        client_request_id=None,
        source_type="external_live",
        arrival_ts=now,
        latest_finish_ts=now + timedelta(hours=2),
        requested_energy_kwh=20.0,
        requested_duration_minutes=30,
        preference_mode="closest",
        charger_type_preference=charger_type_preference,
        zone_id="zone-a",
        vehicle_max_ac_kw=vehicle_max_ac_kw,
        vehicle_max_dc_kw=vehicle_max_dc_kw,
    )


def build_env(*, station: Station) -> DundeeEnv:
    env = DundeeEnv.__new__(DundeeEnv)
    env.station_index = {station.station_id: station}
    env.stations_runtime = {station.station_id: StationRuntimeState(station=station)}
    env.active_sessions = {}
    env.requests = {}
    return env


def test_charging_connector_backwards_compatible_and_extended_fields() -> None:
    legacy = ChargingConnector("legacy", 22.0)
    detailed = ChargingConnector("cp-rapid", 150.0, connector_type="rapid", cp_id="cp-rapid")

    assert legacy.connector_id == "legacy"
    assert legacy.max_power_kw == 22.0
    assert legacy.connector_type == "unknown"
    assert legacy.cp_id is None
    assert detailed.connector_type == "rapid"
    assert detailed.cp_id == "cp-rapid"


def test_build_station_index_uses_chargepoint_rows_and_falls_back_to_synthetic() -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    bundle = SimpleNamespace(
        stations=SimpleNamespace(
            to_dict=lambda orient: [
                {
                    "station_id": "cp-backed",
                    "station_name": "CP Backed",
                    "zone_id": "zone-a",
                    "transformer_id": "tx-1",
                    "latitude": 56.46,
                    "longitude": -2.97,
                    "cp_count_total": 2,
                    "connector_mix_total": "ac;rapid",
                    "station_capacity_kw_assumed": 172.0,
                },
                {
                    "station_id": "fallback",
                    "station_name": "Fallback",
                    "zone_id": "zone-b",
                    "transformer_id": "tx-2",
                    "latitude": 56.47,
                    "longitude": -2.98,
                    "cp_count_total": 2,
                    "connector_mix_total": "ac",
                    "station_capacity_kw_assumed": 44.0,
                },
            ]
        ),
        chargepoints=SimpleNamespace(
            to_dict=lambda orient: [
                {
                    "cp_id": "cp-ac",
                    "station_id": "cp-backed",
                    "connector_type_mode": "ac",
                    "assumed_port_kw": 22.0,
                },
                {
                    "cp_id": "cp-rapid",
                    "station_id": "cp-backed",
                    "connector_type_mode": "rapid",
                    "assumed_port_kw": 150.0,
                },
            ]
        ),
    )

    stations = env._build_station_index(bundle)

    assert len(stations) == 2
    cp_backed = stations["cp-backed"]
    assert [connector.connector_id for connector in cp_backed.connectors] == ["cp-ac", "cp-rapid"]
    assert [connector.connector_type for connector in cp_backed.connectors] == ["ac", "rapid"]
    assert [connector.max_power_kw for connector in cp_backed.connectors] == [22.0, 150.0]

    fallback = stations["fallback"]
    assert len(fallback.connectors) == 2
    assert all(connector.connector_type == "ac" for connector in fallback.connectors)
    assert all(connector.max_power_kw == 22.0 for connector in fallback.connectors)


def test_cp_compatibility_filters_available_connectors_by_requested_type() -> None:
    station = build_station(
        "multi",
        connectors=(
            ChargingConnector("ac-1", 22.0, connector_type="ac", cp_id="ac-1"),
            ChargingConnector("rapid-1", 50.0, connector_type="rapid", cp_id="rapid-1"),
            ChargingConnector("ultra-1", 150.0, connector_type="ultra_rapid", cp_id="ultra-1"),
        ),
    )
    env = build_env(station=station)

    assert [connector.connector_id for connector in env._available_compatible_connectors("multi", "AC")] == ["ac-1"]
    assert [connector.connector_id for connector in env._available_compatible_connectors("multi", "Rapid")] == [
        "rapid-1",
        "ultra-1",
    ]
    assert [connector.connector_id for connector in env._available_compatible_connectors("multi", "UltraRapid")] == [
        "ultra-1"
    ]
    assert [connector.connector_id for connector in env._available_compatible_connectors("multi", "Any")] == [
        "ac-1",
        "rapid-1",
        "ultra-1",
    ]


def test_available_compatible_ports_drop_when_matching_connector_is_busy() -> None:
    station = build_station(
        "mixed",
        connectors=(
            ChargingConnector("ac-1", 22.0, connector_type="ac", cp_id="ac-1"),
            ChargingConnector("rapid-1", 50.0, connector_type="rapid", cp_id="rapid-1"),
        ),
    )
    env = build_env(station=station)
    rapid_request = build_request(charger_type_preference="Rapid")
    env.active_sessions[rapid_request.request_id] = SimpleNamespace(connector_id="rapid-1")
    env.stations_runtime[station.station_id].active_session_ids.append(rapid_request.request_id)

    assert env._station_free_ports("mixed") == 1
    assert env._station_free_compatible_ports("mixed", "Rapid") == 0
    assert env._compatible_available_port_count(rapid_request, station) == 0


def test_best_available_connector_power_respects_connector_type_and_vehicle_limits() -> None:
    station = build_station(
        "power-station",
        connectors=(
            ChargingConnector("ac-1", 22.0, connector_type="ac", cp_id="ac-1"),
            ChargingConnector("rapid-1", 150.0, connector_type="rapid", cp_id="rapid-1"),
        ),
    )
    env = build_env(station=station)

    assert env._best_available_connector_power_kw(build_request(charger_type_preference="AC"), station) == 22.0
    assert env._best_available_connector_power_kw(build_request(charger_type_preference="Rapid"), station) == 150.0
    assert (
        env._best_available_connector_power_kw(
            build_request(charger_type_preference="Rapid", vehicle_max_dc_kw=50.0),
            station,
        )
        == 50.0
    )
    assert (
        env._best_available_connector_power_kw(
            build_request(charger_type_preference="AC", vehicle_max_ac_kw=11.0),
            station,
        )
        == 11.0
    )


def test_start_session_assigns_connector_id_and_type() -> None:
    station = build_station(
        "session-station",
        connectors=(
            ChargingConnector("rapid-1", 50.0, connector_type="rapid", cp_id="rapid-1"),
            ChargingConnector("rapid-2", 150.0, connector_type="rapid", cp_id="rapid-2"),
        ),
        connector_mix_total="rapid",
    )
    env = build_env(station=station)
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._record_event = lambda *args, **kwargs: None
    request = build_request(charger_type_preference="Rapid", vehicle_max_dc_kw=120.0)
    option = SimpleNamespace(
        station_id=station.station_id,
        transformer_id=station.transformer_id,
        zone_id=station.zone_id,
        estimated_duration_minutes=15,
        estimated_cost_gbp=5.0,
    )

    env._start_session(request, option)

    session = env.active_sessions[request.request_id]
    assert session.connector_id == "rapid-2"
    assert session.connector_type == "rapid"
