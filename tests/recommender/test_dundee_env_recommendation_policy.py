from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from datetime import datetime, timedelta
import importlib

import pytest

for module_name in ("numpy", "pandas"):
    try:
        importlib.import_module(module_name)
    except ImportError:
        module = types.ModuleType(module_name)
        module.DataFrame = object
        sys.modules.setdefault(module_name, module)

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationResponse
from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import SimulationRequest, Station
from ev_core.recommender.ranker import CandidateContext
from ev_core.routing.providers import RouteEstimate
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


class CapturingRecommendationService:
    def __init__(self) -> None:
        self.seen_policy_name: str | None = None
        self.seen_runtime_context = None
        self.seen_policy_selection_metadata = None
        self.seen_preference_mode = None
        self.seen_candidate_contexts = None

    def recommend(self, **kwargs):
        self.seen_policy_name = kwargs["policy_name"]
        self.seen_runtime_context = kwargs.get("runtime_context")
        self.seen_policy_selection_metadata = kwargs.get("policy_selection_metadata")
        self.seen_preference_mode = kwargs.get("preference_mode")
        self.seen_candidate_contexts = kwargs.get("candidate_contexts")
        return RecommendationResponse(
            request_id=kwargs["request_id"],
            client_request_id=kwargs["client_request_id"],
            simulated_timestamp=kwargs["simulated_timestamp"],
            zone_id=kwargs["zone_id"],
            top_recommendation=None,
            alternatives=[],
            source_type=kwargs["source_type"],
            metadata=kwargs.get("policy_selection_metadata") or {},
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


def priced_candidate() -> CandidateContext:
    base = candidate()
    return CandidateContext(
        **{
            **base.__dict__,
            "metadata": {
                "dynamic_pricing_enabled": True,
                "final_price_per_kwh": 0.42,
            },
        }
    )


def feeder_context_result() -> SimpleNamespace:
    return SimpleNamespace(
        runtime_context={
            "feeder_observation": [0.0],
            "feeder_action_mask": [True],
            "feeder_station_ids": ["station-a"],
        },
        metadata={
            "feeder_context_available": True,
            "feeder_action_count": 1,
            "offline_feeder_rl_adapter": True,
        },
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


def test_get_ranked_recommendations_builds_feeder_context_for_feeder_policy(monkeypatch) -> None:
    from ev_core.env import dundee_env

    env = DundeeEnv.__new__(DundeeEnv)
    service = CapturingRecommendationService()
    env.recommendation_service = service
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._build_candidate_contexts = lambda request: [candidate()]
    env._record_event = lambda *args, **kwargs: None

    def fake_build_feeder_runtime_context(request, **kwargs):
        return SimpleNamespace(
            runtime_context={
                "feeder_observation": [0.0],
                "feeder_action_mask": [True],
                "feeder_station_ids": ["station-a"],
            },
            metadata={
                "feeder_context_available": True,
                "feeder_action_count": 1,
                "offline_feeder_rl_adapter": True,
            },
        )

    monkeypatch.setattr(dundee_env, "build_feeder_runtime_context", fake_build_feeder_runtime_context)

    env.get_ranked_recommendations(
        simulation_request(),
        recommendation_policy_name="rl_maskable_ppo_feeder",
        policy_selection_metadata={"effective_policy_name": "rl_maskable_ppo_feeder"},
    )

    assert service.seen_policy_name == "rl_maskable_ppo_feeder"
    assert service.seen_runtime_context["feeder_action_mask"] == [True]
    assert service.seen_policy_selection_metadata["feeder_context_available"] is True
    assert service.seen_policy_selection_metadata["offline_feeder_rl_adapter"] is True


@pytest.mark.parametrize(
    "policy_name",
    [
        "rl_safety_closest",
        "rl_safety_cheapest",
        "rl_safety_fastest",
        "rl_safety_weighted",
        "rl_safety_preference",
    ],
)
def test_get_ranked_recommendations_builds_feeder_context_for_safety_policies(
    monkeypatch,
    policy_name: str,
) -> None:
    from ev_core.env import dundee_env

    env = DundeeEnv.__new__(DundeeEnv)
    service = CapturingRecommendationService()
    env.recommendation_service = service
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._build_candidate_contexts = lambda request: [priced_candidate()]
    env._record_event = lambda *args, **kwargs: None
    build_calls = []

    def fake_build_feeder_runtime_context(request, **kwargs):
        build_calls.append((request, kwargs))
        return feeder_context_result()

    monkeypatch.setattr(
        dundee_env,
        "build_feeder_runtime_context",
        fake_build_feeder_runtime_context,
    )
    safety_metadata = {
        "effective_policy_name": policy_name,
        "rl_safety_filter_enabled": True,
        "rl_safety_filter_mode": "penalty",
        "rl_safety_filter_strict": True,
        "rl_safety_filter_penalty_weight": 0.4,
        "rl_safety_block_unsafe": False,
        "rl_safety_mapping_mode": "exact_only",
    }

    env.get_ranked_recommendations(
        simulation_request(),
        recommendation_policy_name=policy_name,
        policy_selection_metadata=safety_metadata,
    )

    assert len(build_calls) == 1
    assert service.seen_policy_name == policy_name
    assert service.seen_runtime_context["feeder_action_mask"] == [True]
    for key, value in safety_metadata.items():
        if key.startswith("rl_safety_"):
            assert service.seen_runtime_context[key] == value
    assert service.seen_preference_mode == "closest"
    assert service.seen_candidate_contexts[0].metadata == {
        "dynamic_pricing_enabled": True,
        "final_price_per_kwh": 0.42,
    }


@pytest.mark.parametrize(
    "policy_name",
    ["closest", "cheapest", "fastest", "weighted_score"],
)
def test_get_ranked_recommendations_skips_feeder_context_for_normal_policies(
    monkeypatch,
    policy_name: str,
) -> None:
    from ev_core.env import dundee_env

    env = DundeeEnv.__new__(DundeeEnv)
    service = CapturingRecommendationService()
    env.recommendation_service = service
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._build_candidate_contexts = lambda request: [candidate()]
    env._record_event = lambda *args, **kwargs: None

    def fail_if_called(*args, **kwargs):
        raise AssertionError("normal deterministic policies do not need feeder context")

    monkeypatch.setattr(
        dundee_env,
        "build_feeder_runtime_context",
        fail_if_called,
    )

    env.get_ranked_recommendations(
        simulation_request(),
        recommendation_policy_name=policy_name,
        policy_selection_metadata={"rl_safety_filter_enabled": False},
    )

    assert service.seen_policy_name == policy_name
    assert "feeder_context_available" not in service.seen_runtime_context


def test_get_ranked_recommendations_builds_feeder_context_when_safety_is_automatic(
    monkeypatch,
) -> None:
    from ev_core.env import dundee_env

    env = DundeeEnv.__new__(DundeeEnv)
    service = CapturingRecommendationService()
    env.recommendation_service = service
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._build_candidate_contexts = lambda request: [candidate()]
    env._record_event = lambda *args, **kwargs: None
    build_calls = []

    def fake_build_feeder_runtime_context(request, **kwargs):
        build_calls.append((request, kwargs))
        return feeder_context_result()

    monkeypatch.setattr(
        dundee_env,
        "build_feeder_runtime_context",
        fake_build_feeder_runtime_context,
    )

    env.get_ranked_recommendations(
        simulation_request(),
        recommendation_policy_name="closest",
        policy_selection_metadata={"rl_safety_filter_enabled": True},
    )

    assert len(build_calls) == 1
    assert service.seen_runtime_context["feeder_context_available"] is True


def test_get_ranked_recommendations_skips_feeder_context_for_deterministic_policy(monkeypatch) -> None:
    from ev_core.env import dundee_env

    env = DundeeEnv.__new__(DundeeEnv)
    service = CapturingRecommendationService()
    env.recommendation_service = service
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._build_candidate_contexts = lambda request: [candidate()]
    env._record_event = lambda *args, **kwargs: None

    def fail_if_called(*args, **kwargs):
        raise AssertionError("feeder context should only be built for rl_maskable_ppo_feeder")

    monkeypatch.setattr(dundee_env, "build_feeder_runtime_context", fail_if_called)

    env.get_ranked_recommendations(
        simulation_request(),
        recommendation_policy_name="cheapest",
    )

    assert service.seen_policy_name == "cheapest"
    assert service.seen_runtime_context == {"simulated_timestamp": env.current_time}


class CapturingCandidateBuilder:
    def __init__(self) -> None:
        self.seen_kwargs = None

    def build(self, **kwargs):
        self.seen_kwargs = kwargs
        return [candidate()]


def test_build_candidate_contexts_delegates_to_candidate_builder() -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    builder = CapturingCandidateBuilder()
    request = simulation_request()
    env.candidate_builder = builder
    env.station_index = {"station-1": object()}
    env.stations_runtime = {"station-1": object()}
    env.current_time = datetime(2024, 6, 10, 12, 0)
    env._distance_to_station_km = lambda request, station: 1.0
    env._estimate_station_wait_minutes = lambda station_id: 0
    env._current_price_per_kwh = lambda: 0.25
    env._current_transformer_headroom = lambda transformer_id: 100.0
    env._is_charger_compatible = lambda requested_type, connector_mix: True

    env._current_station_price_per_kwh = lambda station_id: 0.25
    env._current_station_pricing_metadata = lambda station_id: {"price_per_kwh": 0.25}
    env._candidate_station_price_per_kwh = lambda request, station: 0.4
    env._candidate_station_pricing_metadata = lambda request, station: {"price_per_kwh": 0.4}

    result = env._build_candidate_contexts(request, only_station_id="station-1")

    assert result == [candidate()]
    assert builder.seen_kwargs is not None
    assert builder.seen_kwargs["only_station_id"] == "station-1"
    assert list(builder.seen_kwargs["stations"]) == [env.station_index["station-1"]]
    assert builder.seen_kwargs["stations_runtime"] == env.stations_runtime
    assert builder.seen_kwargs["station_effective_power_kw"] == env._best_available_connector_power_kw
    assert builder.seen_kwargs["compatible_available_port_count"] == env._compatible_available_port_count
    station = env.station_index["station-1"]
    assert builder.seen_kwargs["station_price_per_kwh"]("station-1") == 0.4
    assert builder.seen_kwargs["station_pricing_metadata"]("station-1") == {"price_per_kwh": 0.4}
    assert env._candidate_station_price_per_kwh(request, station) == 0.4
    assert env._candidate_station_pricing_metadata(request, station) == {"price_per_kwh": 0.4}


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


def test_distance_to_station_km_uses_routing_provider_estimate() -> None:
    class FakeRoutingProvider:
        name = "fake"

        def estimate_route(self, request, station):
            return RouteEstimate(distance_km=7.25, provider=self.name)

    env = DundeeEnv.__new__(DundeeEnv)
    env.routing_provider = FakeRoutingProvider()
    station = SimpleNamespace(station_id="station-1", zone_id="zone")

    assert env._distance_to_station_km(simulation_request(), station) == 7.25


def test_distance_simple_preserves_existing_formula() -> None:
    env = DundeeEnv.__new__(DundeeEnv)

    result = env._distance_simple(56.462, -2.97, 56.46, -2.98)
    expected = (((56.462 - 56.46) * 111.0) ** 2 + (((-2.97) - (-2.98)) * (111.0 * 0.56)) ** 2) ** 0.5

    assert result == expected


def test_distance_simple_uses_default_far_fallback_when_origin_missing() -> None:
    env = DundeeEnv.__new__(DundeeEnv)

    assert env._distance_simple(None, None, 56.46, -2.98) == 3.0


def test_default_routing_provider_matches_legacy_distance_behavior() -> None:
    env = DundeeEnv.__new__(DundeeEnv)
    env.routing_provider = SimpleDistanceRoutingProvider()
    request = simulation_request()
    request.current_latitude = 56.462
    request.current_longitude = -2.97
    station = Station(
        station_id="station-1",
        station_name="Station 1",
        zone_id="zone",
        transformer_id="tx",
        latitude=56.46,
        longitude=-2.98,
        cp_count_total=2,
        connector_mix_total="rapid",
        station_capacity_kw_assumed=64.0,
    )

    assert env._distance_to_station_km(request, station) == env._distance_simple(
        request.current_latitude,
        request.current_longitude,
        station.latitude,
        station.longitude,
    )
