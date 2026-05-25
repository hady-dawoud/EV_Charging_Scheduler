from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import ChargingConnector, GridContext, Station, StationRuntimeState, Transformer
from ev_core.recommender.candidates import CandidateBuilder
from ev_core.recommender.eligibility import StationEligibilityFilter
from ev_core.recommender.service import RecommendationService
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


NOW = datetime(2024, 6, 10, 12, 0)


def station(station_id: str, connectors: tuple[ChargingConnector, ...]) -> Station:
    return Station(
        station_id=station_id,
        station_name=station_id.replace("-", " ").title(),
        zone_id="zone_central_waterfront",
        transformer_id="tx-1",
        latitude=56.462,
        longitude=-2.9707,
        cp_count_total=len(connectors),
        connector_mix_total=";".join(connector.connector_type for connector in connectors),
        station_capacity_kw_assumed=sum(connector.max_power_kw for connector in connectors),
        connectors=connectors,
    )


def env_with_stations(stations: tuple[Station, ...]) -> DundeeEnv:
    env = DundeeEnv.__new__(DundeeEnv)
    env.candidate_builder = CandidateBuilder()
    env.station_eligibility_filter = StationEligibilityFilter()
    env.recommendation_service = RecommendationService()
    env.current_time = NOW
    env.dynamic_pricing_enabled = True
    env.routing_provider = SimpleDistanceRoutingProvider()
    env.last_routing_fallback_reason = None
    env._route_estimate_cache = {}
    env.requests = {}
    env.active_sessions = {}
    env.recent_events = []
    env.station_index = {item.station_id: item for item in stations}
    env.stations_runtime = {item.station_id: StationRuntimeState(station=item) for item in stations}
    env.transformer_index = {
        "tx-1": Transformer(
            transformer_id="tx-1",
            transformer_name="Transformer 1",
            zone_id="zone_central_waterfront",
            capacity_kw=500.0,
            attached_station_ids=tuple(item.station_id for item in stations),
        )
    }
    env._record_event = lambda *args, **kwargs: None
    env._current_transformer_context = lambda transformer_id: GridContext(
        interval_start=env.current_time,
        background_load_kw=20.0,
        tariff_per_kwh=0.25,
        pv_generation_kw=0.0,
    )
    return env


def external_request(
    *,
    charger_type: str,
    request_id: str = "request-1",
    preference_mode: str = "Fastest",
    requested_energy_kwh: float = 20.0,
    vehicle_max_ac_kw: float | None = None,
    vehicle_max_dc_kw: float | None = None,
) -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id=f"client-{request_id}",
        request_timestamp=NOW,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=requested_energy_kwh,
        preference_mode=preference_mode,
        charger_type=charger_type,
        latest_finish_ts=NOW + timedelta(hours=6),
        source_type="external_live",
        request_id=request_id,
        zone_id="zone_central_waterfront",
        vehicle_max_ac_kw=vehicle_max_ac_kw,
        vehicle_max_dc_kw=vehicle_max_dc_kw,
    )


def contexts_for(env: DundeeEnv, request: ExternalChargingRequest):
    simulation_request = env._build_simulation_request_from_external(request)
    return simulation_request, env._build_candidate_contexts(simulation_request)


def test_mobile_dc_payload_reaches_runtime_as_dc_request_and_maps_to_rapid(monkeypatch) -> None:
    fake_user_module = types.ModuleType("app.models.user")
    fake_user_module.User = object
    monkeypatch.setitem(sys.modules, "app.models.user", fake_user_module)
    mobile_schema = importlib.import_module("app.schemas.mobile_recommendations")
    mobile_service = importlib.import_module("app.services.mobile_recommendations_service")
    seen = {}

    def fake_generate_recommendations(request, *, recommendation_policy_name=None):
        seen["request"] = request
        seen["recommendation_policy_name"] = recommendation_policy_name
        return None

    monkeypatch.setattr(mobile_service, "generate_recommendations", fake_generate_recommendations)
    request = mobile_schema.MobileRecommendationRequest.model_validate(
        {
            "latitude": 56.462,
            "longitude": -2.9707,
            "battery_level": 45,
            "target_battery_level": 80,
            "battery_kwh": 60,
            "requested_energy_kwh": 21,
            "preference_mode": "Fastest",
            "connector_type": "DC",
            "latest_finish_minutes_from_now": 120,
            "zone_id": "zone_central_waterfront",
        }
    )

    mobile_service.generate_mobile_recommendations(request, current_user=SimpleNamespace(id="user-1"))

    runtime_request = seen["request"]
    assert runtime_request.preference_mode == "fastest"
    assert runtime_request.charger_type == "DC"
    assert seen["recommendation_policy_name"] is None

    env = env_with_stations(
        (station("rapid", (ChargingConnector("rapid-50", 50.0, connector_type="rapid"),)),)
    )
    simulation_request = env._build_simulation_request_from_external(runtime_request)
    assert simulation_request.charger_type_preference == "Rapid"


def test_dc_request_finds_rapid_and_ultra_rapid_connectors_not_ac_only() -> None:
    env = env_with_stations(
        (
            station("ac", (ChargingConnector("ac-22", 22.0, connector_type="ac"),)),
            station("rapid", (ChargingConnector("rapid-50", 50.0, connector_type="rapid"),)),
            station("ultra", (ChargingConnector("ultra-150", 150.0, connector_type="ultra_rapid"),)),
        )
    )

    simulation_request, contexts = contexts_for(env, external_request(charger_type="DC"))

    assert simulation_request.charger_type_preference == "Rapid"
    assert {context.station_id for context in contexts} == {"rapid", "ultra"}
    assert {context.metadata["selected_connector_type"] for context in contexts} == {"rapid", "ultra_rapid"}


def test_ac_request_does_not_use_rapid_only_connectors() -> None:
    env = env_with_stations(
        (
            station("ac", (ChargingConnector("ac-22", 22.0, connector_type="ac"),)),
            station("rapid", (ChargingConnector("rapid-50", 50.0, connector_type="rapid"),)),
        )
    )

    _, contexts = contexts_for(env, external_request(charger_type="AC"))

    assert [context.station_id for context in contexts] == ["ac"]
    assert contexts[0].metadata["selected_connector_type"] == "ac"


def test_any_request_uses_best_compatible_connector_for_duration_and_pricing() -> None:
    env = env_with_stations(
        (
            station(
                "mixed",
                (
                    ChargingConnector("ac-22", 22.0, connector_type="ac"),
                    ChargingConnector("rapid-50", 50.0, connector_type="rapid"),
                    ChargingConnector("ultra-150", 150.0, connector_type="ultra_rapid"),
                ),
            ),
        )
    )

    _, contexts = contexts_for(env, external_request(charger_type="Any"))
    context = contexts[0]

    assert context.metadata["selected_connector_type"] == "ultra_rapid"
    assert context.metadata["selected_connector_power_kw"] == 150.0
    assert context.metadata["effective_power_kw"] == 150.0
    assert context.metadata["tariff_class"] == "ultra_rapid"
    assert context.estimated_duration_minutes == 15


def test_response_duration_cost_and_metadata_use_same_selected_connector() -> None:
    env = env_with_stations(
        (
            station(
                "mixed",
                (
                    ChargingConnector("ac-22", 22.0, connector_type="ac"),
                    ChargingConnector("rapid-150", 150.0, connector_type="rapid"),
                ),
            ),
        )
    )

    response = env.get_ranked_recommendations(
        external_request(
            charger_type="DC",
            requested_energy_kwh=40.0,
            vehicle_max_dc_kw=50.0,
        )
    )

    top = response.top_recommendation
    assert top is not None
    metadata = top.metadata
    assert metadata["selected_connector_type"] == "rapid"
    assert metadata["selected_connector_power_kw"] == 150.0
    assert metadata["effective_power_kw"] == 50.0
    assert metadata["tariff_class"] == "ultra_rapid"
    assert top.estimated_duration_minutes == 45
    assert abs(top.estimated_cost_gbp - (40.0 * metadata["final_price_per_kwh"])) <= 0.01
