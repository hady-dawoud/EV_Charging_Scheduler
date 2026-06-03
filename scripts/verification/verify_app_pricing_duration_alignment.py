"""Verify app-facing recommendation pricing and duration metadata alignment."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.env.dundee_env import DundeeEnv
from ev_core.env.entities import ChargingConnector, GridContext, Station, StationRuntimeState, Transformer
from ev_core.recommender.candidates import CandidateBuilder
from ev_core.recommender.eligibility import StationEligibilityFilter
from ev_core.recommender.service import RecommendationService
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


NOW = datetime(2024, 6, 10, 12, 0)


def build_station(station_id: str, connector_type: str, power_kw: float) -> Station:
    return Station(
        station_id=station_id,
        station_name=station_id.replace("-", " ").title(),
        zone_id="zone_central_waterfront",
        transformer_id="tx-1",
        latitude=56.462,
        longitude=-2.9707,
        cp_count_total=1,
        connector_mix_total=connector_type,
        station_capacity_kw_assumed=power_kw,
        connectors=(ChargingConnector(f"{station_id}-cp", power_kw, connector_type=connector_type),),
    )


def build_env(station: Station, *, background_load_kw: float = 20.0) -> DundeeEnv:
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
    env.station_index = {station.station_id: station}
    env.stations_runtime = {station.station_id: StationRuntimeState(station=station)}
    env.transformer_index = {
        "tx-1": Transformer(
            transformer_id="tx-1",
            transformer_name="Transformer 1",
            zone_id="zone_central_waterfront",
            capacity_kw=500.0,
            attached_station_ids=(station.station_id,),
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


def request_for(case_name: str, *, energy_kwh: float, charger_type: str) -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id=f"verify-{case_name}",
        request_timestamp=NOW,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=energy_kwh,
        preference_mode="Cheapest",
        charger_type=charger_type,
        latest_finish_ts=NOW + timedelta(hours=6),
        source_type="external_live",
        request_id=f"verify-{case_name}",
        zone_id="zone_central_waterfront",
        vehicle_max_ac_kw=22.0,
        vehicle_max_dc_kw=150.0,
    )


def verify_case(case_name: str, *, connector_type: str, power_kw: float, charger_type: str, energy_kwh: float) -> bool:
    station = build_station(case_name, connector_type, power_kw)
    env = build_env(station)
    request = request_for(case_name, energy_kwh=energy_kwh, charger_type=charger_type)
    response = env.get_ranked_recommendations(request)
    top = response.top_recommendation
    if top is None:
        print(f"{case_name}: FAIL no recommendation")
        return False

    metadata = top.metadata
    recomputed_cost = float(request.requested_energy_kwh) * float(metadata["final_price_per_kwh"])
    duration_power = float(metadata["effective_power_kw"])
    expected_duration = max(int(round((energy_kwh / duration_power) * 60.0 / 15) * 15), 15)
    passed = (
        abs(top.estimated_cost_gbp - recomputed_cost) <= 0.01
        and top.estimated_duration_minutes == expected_duration
    )
    print(f"case: {case_name}")
    print(f"  request_energy_kwh: {energy_kwh}")
    print(f"  requested_charger_type: {charger_type}")
    print(f"  selected_station: {top.station_id}")
    print(f"  selected_connector_type: {metadata.get('selected_connector_type')}")
    print(f"  selected_connector_power_kw: {metadata.get('selected_connector_power_kw')}")
    print(f"  effective_power_kw: {metadata.get('effective_power_kw')}")
    print(f"  estimated_duration_min: {top.estimated_duration_minutes}")
    print(f"  tariff_class: {metadata.get('tariff_class')}")
    print(f"  base_price_per_kwh: {metadata.get('base_price_per_kwh')}")
    print(f"  dynamic_multiplier: {metadata.get('total_dynamic_multiplier')}")
    print(f"  final_price_per_kwh: {metadata.get('final_price_per_kwh')}")
    print(f"  estimated_cost: {round(top.estimated_cost_gbp, 4)}")
    print(f"  recomputed_cost: {round(recomputed_cost, 4)}")
    print(f"  result: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> int:
    cases = [
        ("ac_standard", "ac", 7.0, "AC"),
        ("ac_fast", "ac", 22.0, "AC"),
        ("rapid", "rapid", 50.0, "DC"),
        ("ultra_rapid", "ultra_rapid", 150.0, "DC"),
    ]
    results = [
        verify_case(case_name, connector_type=connector_type, power_kw=power_kw, charger_type=charger_type, energy_kwh=20.0)
        for case_name, connector_type, power_kw, charger_type in cases
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
