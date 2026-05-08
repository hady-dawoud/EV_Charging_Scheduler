from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from ev_core.data.repositories import DundeeDataBundle
from ev_core.env.entities import ActiveChargingSession, SimulationRequest
from ev_core.env.environment import DundeeEnv
from ev_core.forecasting.provider import ForecastProvider, ForecastRequest, ForecastSeries


class StaticForecastProvider:
    def __init__(
        self,
        *,
        background_load_by_transformer: dict[str, float] | None = None,
        price_gbp_per_kwh: float = 0.25,
        pv_generation_kw_per_mw: float = 0.0,
    ) -> None:
        self.background_load_by_transformer = background_load_by_transformer or {}
        self.price_gbp_per_kwh = price_gbp_per_kwh
        self.pv_generation_kw_per_mw = pv_generation_kw_per_mw

    def forecast_background_load(self, request: ForecastRequest) -> ForecastSeries:
        value = self.background_load_by_transformer.get(request.series_name, request.default_value)
        return ForecastSeries(
            series_name=request.series_name,
            timestamps=request.timestamps,
            values=tuple(float(value) for _ in request.timestamps),
            unit="kW",
        )

    def forecast_price(self, request: ForecastRequest) -> ForecastSeries:
        return ForecastSeries(
            series_name=request.series_name,
            timestamps=request.timestamps,
            values=tuple(float(self.price_gbp_per_kwh) for _ in request.timestamps),
            unit="GBP_per_kWh",
        )

    def forecast_pv_generation(self, request: ForecastRequest) -> ForecastSeries:
        return ForecastSeries(
            series_name=request.series_name,
            timestamps=request.timestamps,
            values=tuple(float(self.pv_generation_kw_per_mw) for _ in request.timestamps),
            unit="kW_per_MW",
        )


def _minimal_bundle() -> DundeeDataBundle:
    stations = pd.DataFrame(
        [
            {
                "station_id": "station_a",
                "station_name": "Station A",
                "zone_id": "zone_a",
                "transformer_id": "tx_a",
                "latitude": 56.46,
                "longitude": -2.97,
                "cp_count_total": 2,
                "connector_mix_total": "rapid",
                "station_capacity_kw_assumed": 100.0,
            },
            {
                "station_id": "station_b",
                "station_name": "Station B",
                "zone_id": "zone_a",
                "transformer_id": "tx_b",
                "latitude": 56.4605,
                "longitude": -2.9705,
                "cp_count_total": 2,
                "connector_mix_total": "rapid",
                "station_capacity_kw_assumed": 100.0,
            },
        ]
    )
    transformers = pd.DataFrame(
        [
            {
                "transformer_id": "tx_a",
                "transformer_name": "Transformer A",
                "zone_id": "zone_a",
                "transformer_capacity_kw_assumed": 100.0,
            },
            {
                "transformer_id": "tx_b",
                "transformer_name": "Transformer B",
                "zone_id": "zone_a",
                "transformer_capacity_kw_assumed": 100.0,
            },
        ]
    )
    replay = pd.DataFrame(
        [
            {
                "request_id": "request_a",
                "arrival_slot": pd.Timestamp("2024-06-10T12:00:00"),
            }
        ]
    )
    return DundeeDataBundle(
        stations=stations,
        transformers=transformers,
        zones=pd.DataFrame([{"zone_id": "zone_a"}]),
        chargepoints=pd.DataFrame(),
        replay_requests_2023=replay,
        replay_requests_2024=replay,
        request_generator_params={},
        background_load=pd.DataFrame(),
        price_table=pd.DataFrame(),
        pv_profile=pd.DataFrame(),
    )


def _request() -> SimulationRequest:
    now = datetime(2024, 6, 10, 12, 0)
    return SimulationRequest(
        request_id="request-1",
        client_request_id="client-1",
        source_type="external_live",
        arrival_ts=now,
        latest_finish_ts=now + timedelta(hours=2),
        requested_energy_kwh=20.0,
        requested_duration_minutes=30,
        preference_mode="cheapest",
        charger_type_preference="Rapid",
        current_latitude=56.46,
        current_longitude=-2.97,
        zone_id="zone_a",
    )


def _env(*, dynamic_pricing_enabled: bool = True) -> DundeeEnv:
    return DundeeEnv(
        _minimal_bundle(),
        start_time=datetime(2024, 6, 10, 12, 0),
        forecast_provider=StaticForecastProvider(
            background_load_by_transformer={"tx_a": 20.0, "tx_b": 20.0},
            price_gbp_per_kwh=0.25,
        ),
        dynamic_pricing_enabled=dynamic_pricing_enabled,
    )


def test_station_price_can_drop_to_or_below_base_under_low_transformer_load() -> None:
    env = _env(dynamic_pricing_enabled=True)

    base_price = env._current_price_per_kwh()
    station_price = env._current_station_price_per_kwh("station_a")

    assert station_price <= base_price


def test_station_price_increases_when_transformer_is_under_stress() -> None:
    env = _env(dynamic_pricing_enabled=True)
    env.active_sessions["session-busy"] = ActiveChargingSession(
        request_id="session-busy",
        station_id="station_b",
        transformer_id="tx_b",
        started_at=env.current_time,
        expected_completion_ts=env.current_time + timedelta(minutes=45),
        assigned_power_kw=70.0,
        estimated_cost_gbp=0.0,
    )
    env.stations_runtime["station_b"].active_session_ids.append("session-busy")

    base_price = env._current_price_per_kwh()
    station_price = env._current_station_price_per_kwh("station_b")

    assert station_price > base_price


def test_cheapest_policy_prefers_lower_dynamic_cost_station() -> None:
    env = _env(dynamic_pricing_enabled=True)
    env.active_sessions["session-busy"] = ActiveChargingSession(
        request_id="session-busy",
        station_id="station_b",
        transformer_id="tx_b",
        started_at=env.current_time,
        expected_completion_ts=env.current_time + timedelta(minutes=45),
        assigned_power_kw=70.0,
        estimated_cost_gbp=0.0,
    )
    env.stations_runtime["station_b"].active_session_ids.append("session-busy")

    response = env.get_ranked_recommendations(_request(), recommendation_policy_name="cheapest")

    assert response.top_recommendation is not None
    assert response.top_recommendation.station_id == "station_a"
    assert response.top_recommendation.estimated_cost_gbp < response.alternatives[0].estimated_cost_gbp
