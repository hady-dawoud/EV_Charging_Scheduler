from __future__ import annotations

from datetime import datetime, timedelta

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import ChargingConnector, GridContext, Station, StationRuntimeState, Transformer
from ev_core.recommender.candidates import CandidateBuilder
from ev_core.recommender.eligibility import StationEligibilityFilter
from ev_core.recommender.service import RecommendationService
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


NOW = datetime(2024, 6, 10, 12, 0)


def station(
    station_id: str,
    *,
    connectors: tuple[ChargingConnector, ...],
    latitude: float = 56.462,
    longitude: float = -2.9707,
) -> Station:
    connector_mix = ";".join(connector.connector_type for connector in connectors)
    return Station(
        station_id=station_id,
        station_name=station_id.replace("-", " ").title(),
        zone_id="zone_central_waterfront",
        transformer_id="tx-1",
        latitude=latitude,
        longitude=longitude,
        cp_count_total=len(connectors),
        connector_mix_total=connector_mix,
        station_capacity_kw_assumed=sum(connector.max_power_kw for connector in connectors),
        connectors=connectors,
    )


def env_with_stations(
    stations: tuple[Station, ...],
    *,
    background_load_kw: float = 20.0,
    transformer_capacity_kw: float = 500.0,
    dynamic_pricing_enabled: bool = True,
) -> DundeeEnv:
    env = DundeeEnv.__new__(DundeeEnv)
    env.candidate_builder = CandidateBuilder()
    env.station_eligibility_filter = StationEligibilityFilter()
    env.recommendation_service = RecommendationService()
    env.current_time = NOW
    env.dynamic_pricing_enabled = dynamic_pricing_enabled
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
            capacity_kw=transformer_capacity_kw,
            attached_station_ids=tuple(item.station_id for item in stations),
        )
    }
    env._record_event = lambda *args, **kwargs: None
    env._current_transformer_context = lambda transformer_id: GridContext(
        interval_start=env.current_time,
        background_load_kw=background_load_kw,
        tariff_per_kwh=0.25,
        pv_generation_kw=0.0,
    )
    return env


def external_request(
    *,
    request_id: str = "request-1",
    requested_energy_kwh: float = 20.0,
    charger_type: str = "Any",
    preference_mode: str = "Cheapest",
    vehicle_max_ac_kw: float | None = None,
    vehicle_max_dc_kw: float | None = None,
    finish_hours: int = 6,
) -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id=f"client-{request_id}",
        request_timestamp=NOW,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=requested_energy_kwh,
        preference_mode=preference_mode,
        charger_type=charger_type,
        latest_finish_ts=NOW + timedelta(hours=finish_hours),
        source_type="external_live",
        request_id=request_id,
        zone_id="zone_central_waterfront",
        vehicle_max_ac_kw=vehicle_max_ac_kw,
        vehicle_max_dc_kw=vehicle_max_dc_kw,
    )


def candidates_for(env: DundeeEnv, request: ExternalChargingRequest):
    simulation_request = env._build_simulation_request_from_external(request)
    return env._build_candidate_contexts(simulation_request)


def test_same_energy_cost_increases_by_dundee_tariff_class() -> None:
    env = env_with_stations(
        (
            station("ac-standard", connectors=(ChargingConnector("ac-7", 7.0, connector_type="ac"),)),
            station("ac-fast", connectors=(ChargingConnector("ac-22", 22.0, connector_type="ac"),)),
            station("rapid", connectors=(ChargingConnector("rapid-50", 50.0, connector_type="rapid"),)),
            station("ultra", connectors=(ChargingConnector("ultra-150", 150.0, connector_type="ultra_rapid"),)),
        )
    )

    by_class = {
        candidate.metadata["tariff_class"]: candidate.estimated_cost_gbp
        for candidate in candidates_for(env, external_request())
    }

    assert by_class["ac_standard"] < by_class["ac_fast"] < by_class["rapid"] < by_class["ultra_rapid"]


def test_dynamic_stress_increases_final_app_cost() -> None:
    target = station("rapid", connectors=(ChargingConnector("rapid-50", 50.0, connector_type="rapid"),))
    low_stress = candidates_for(
        env_with_stations((target,), background_load_kw=20.0, transformer_capacity_kw=100.0),
        external_request(charger_type="DC"),
    )[0]
    high_stress = candidates_for(
        env_with_stations((target,), background_load_kw=95.0, transformer_capacity_kw=100.0),
        external_request(charger_type="DC"),
    )[0]

    assert low_stress.metadata["final_price_per_kwh"] < high_stress.metadata["final_price_per_kwh"]
    assert low_stress.estimated_cost_gbp < high_stress.estimated_cost_gbp


def test_estimated_cost_matches_final_price_times_requested_energy() -> None:
    env = env_with_stations(
        (station("ultra", connectors=(ChargingConnector("ultra-150", 150.0, connector_type="ultra_rapid"),)),)
    )
    request = external_request(requested_energy_kwh=24.5, charger_type="DC")
    candidate = candidates_for(env, request)[0]

    recomputed = request.requested_energy_kwh * candidate.metadata["final_price_per_kwh"]

    assert abs(candidate.estimated_cost_gbp - recomputed) <= 0.01
    assert candidate.metadata["base_price_per_kwh"] == 0.75
    assert candidate.metadata["total_dynamic_multiplier"] > 0


def test_api_response_top_level_shape_is_preserved() -> None:
    env = env_with_stations(
        (station("rapid", connectors=(ChargingConnector("rapid-50", 50.0, connector_type="rapid"),)),)
    )

    response = env.get_ranked_recommendations(external_request(charger_type="DC"))

    assert set(response.model_dump(mode="json")) == {
        "request_id",
        "client_request_id",
        "simulated_timestamp",
        "zone_id",
        "top_recommendation",
        "alternatives",
        "congestion_note",
        "debug_reasoning_summary",
        "source_type",
        "metadata",
    }


def test_ac_duration_uses_vehicle_cap_and_connector_specific_power() -> None:
    env = env_with_stations(
        (
            station(
                "mixed",
                connectors=(
                    ChargingConnector("ac-7", 7.0, connector_type="ac"),
                    ChargingConnector("rapid-150", 150.0, connector_type="rapid"),
                ),
            ),
        )
    )

    candidate = candidates_for(
        env,
        external_request(charger_type="AC", vehicle_max_ac_kw=7.0),
    )[0]

    assert candidate.metadata["selected_connector_type"] == "ac"
    assert candidate.metadata["selected_connector_power_kw"] == 7.0
    assert candidate.metadata["effective_power_kw"] == 7.0
    assert candidate.estimated_duration_minutes == 165


def test_dc_duration_uses_vehicle_cap_and_selected_connector_power() -> None:
    env = env_with_stations(
        (
            station(
                "rapid",
                connectors=(ChargingConnector("rapid-150", 150.0, connector_type="rapid"),),
            ),
        )
    )

    candidate = candidates_for(
        env,
        external_request(requested_energy_kwh=40.0, charger_type="DC", vehicle_max_dc_kw=50.0),
    )[0]

    assert candidate.metadata["selected_connector_type"] == "rapid"
    assert candidate.metadata["selected_connector_power_kw"] == 150.0
    assert candidate.metadata["effective_power_kw"] == 50.0
    assert candidate.estimated_duration_minutes == 45
