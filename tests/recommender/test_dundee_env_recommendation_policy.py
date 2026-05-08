from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from datetime import datetime, timedelta

for module_name in ("numpy", "pandas"):
    module = types.ModuleType(module_name)
    module.DataFrame = object
    sys.modules.setdefault(module_name, module)

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationResponse
from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import SimulationRequest, Station
from ev_core.recommender.ranker import CandidateContext


class CapturingRecommendationService:
    def __init__(self) -> None:
        self.seen_policy_name: str | None = None

    def recommend(self, **kwargs):
        self.seen_policy_name = kwargs["policy_name"]
        return RecommendationResponse(
            request_id=kwargs["request_id"],
            client_request_id=kwargs["client_request_id"],
            simulated_timestamp=kwargs["simulated_timestamp"],
            zone_id=kwargs["zone_id"],
            top_recommendation=None,
            alternatives=[],
            source_type=kwargs["source_type"],
        )


def simulation_request() -> SimulationRequest:
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
        zone_id="zone",
    )


def candidate() -> CandidateContext:
    return CandidateContext(
        station_id="station-1",
        station_name="Station 1",
        zone_id="zone",
        transformer_id="tx",
        distance_km=1.0,
        estimated_wait_minutes=0,
        estimated_duration_minutes=30,
        estimated_cost_gbp=5.0,
        transformer_headroom_kw=200.0,
        current_queue=0,
        utilization=0.1,
        charger_compatible=True,
    )


def test_get_ranked_recommendations_passes_optional_recommendation_policy_name() -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    service = CapturingRecommendationService()
    env.recommendation_service = service
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._build_candidate_contexts = lambda request: [candidate()]
    env._record_event = lambda *args, **kwargs: None

    env.get_ranked_recommendations(
        simulation_request(),
        recommendation_policy_name="closest",
    )

    assert service.seen_policy_name == "closest"


class CapturingCandidateBuilder:
    def __init__(self) -> None:
        self.seen_kwargs = None

    def build(self, **kwargs):
        self.seen_kwargs = kwargs
        return [candidate()]


def test_build_candidate_contexts_delegates_to_candidate_builder() -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    builder = CapturingCandidateBuilder()
    env.candidate_builder = builder
    env.station_index = {"station-1": object()}
    env.stations_runtime = {"station-1": object()}
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._distance_to_station_km = lambda request, station: 1.0
    env._estimate_station_wait_minutes = lambda station_id: 0
    env._current_price_per_kwh = lambda: 0.25
    env._current_transformer_headroom = lambda transformer_id: 100.0
    env._is_charger_compatible = lambda requested_type, connector_mix: True

    result = env._build_candidate_contexts(simulation_request(), only_station_id="station-1")

    assert result == [candidate()]
    assert builder.seen_kwargs is not None
    assert builder.seen_kwargs["only_station_id"] == "station-1"
    assert list(builder.seen_kwargs["stations"]) == [env.station_index["station-1"]]
    assert builder.seen_kwargs["stations_runtime"] == env.stations_runtime
    assert builder.seen_kwargs["station_effective_power_kw"] == env._best_available_connector_power_kw
    assert builder.seen_kwargs["compatible_available_port_count"] == env._compatible_available_port_count


def test_external_vehicle_fields_are_passed_to_simulation_request() -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    request = ExternalChargingRequest.model_validate(
        {
            "client_request_id": "client-1",
            "request_timestamp": datetime(2024, 6, 10, 12, 0),
            "target_soc": 80.0,
            "current_soc": 45.0,
            "battery_kwh": 82.0,
            "requested_energy_kwh": 28.7,
            "vehicle_profile_id": "large_ev",
            "vehicle_max_ac_kw": 11.0,
            "vehicle_max_dc_kw": 150.0,
            "preference_mode": "closest",
            "charger_type": "dc",
            "latest_finish_ts": datetime(2024, 6, 10, 14, 0),
            "source_type": "external_live",
            "request_id": "request-1",
            "zone_id": "zone",
        }
    )

    simulation_request = env._build_simulation_request_from_external(request)

    assert simulation_request.vehicle_profile_id == "large_ev"
    assert simulation_request.vehicle_max_ac_kw == 11.0
    assert simulation_request.vehicle_max_dc_kw == 150.0


def test_station_defaults_preserve_minimal_construction() -> None:
    station = Station(
        station_id="station-1",
        station_name="Station 1",
        zone_id="zone",
        transformer_id="tx",
        latitude=56.46,
        longitude=-2.97,
        cp_count_total=2,
        connector_mix_total="rapid",
        station_capacity_kw_assumed=64.0,
    )

    assert station.is_public is True
    assert station.is_fleet_only is False
    assert station.requires_membership is False
    assert station.needs_followup is False
    assert station.exclude_from_recommendations is False
    assert station.access_notes is None


class FakeStationTable:
    def to_dict(self, orient: str):
        assert orient == "records"
        return [
            {
                "station_id": "station-1",
                "station_name": "Station 1",
                "zone_id": "zone",
                "transformer_id": "tx",
                "latitude": 56.46,
                "longitude": -2.97,
                "cp_count_total": 2,
                "connector_mix_total": "rapid",
                "station_capacity_kw_assumed": 64.0,
                "is_public": "false",
                "is_fleet_only": "1",
                "requires_membership": "yes",
                "needs_followup": "true",
                "exclude_from_recommendations": "0",
                "access_notes": "Depot-only site",
            }
        ]


def test_build_station_index_maps_optional_access_columns() -> None:
    env = DundeeEnv.__new__(DundeeEnv)

    stations = env._build_station_index(SimpleNamespace(stations=FakeStationTable()))
    station = stations["station-1"]

    assert station.is_public is False
    assert station.is_fleet_only is True
    assert station.requires_membership is True
    assert station.needs_followup is True
    assert station.exclude_from_recommendations is False
    assert station.access_notes == "Depot-only site"
