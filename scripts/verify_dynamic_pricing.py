"""Verify the grid-aware dynamic pricing overlay in the Dundee runtime."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.env.entities import ActiveChargingSession
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager


def request_payload(request_id: str) -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id=request_id,
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.970,
        requested_energy_kwh=20.0,
        preference_mode="cheapest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id=request_id,
        zone_id="zone_central_waterfront",
    )


def print_option(prefix: str, option) -> None:
    metadata = option.metadata or {}
    print(prefix)
    print(f"  station_id: {option.station_id}")
    print(f"  transformer_id: {option.transformer_id}")
    print(f"  base_price_per_kwh: {metadata.get('base_price_per_kwh', 'n/a')}")
    print(f"  dynamic_price_per_kwh: {metadata.get('price_per_kwh', 'n/a')}")
    print(f"  transformer_load_ratio: {metadata.get('transformer_load_ratio', 'n/a')}")
    print(f"  headroom_ratio: {metadata.get('transformer_headroom_ratio', 'n/a')}")
    print(f"  pricing_reason: {metadata.get('pricing_reason', 'n/a')}")
    print(f"  estimated_cost_gbp: {round(option.estimated_cost_gbp, 3)}")


def print_station_pricing(env, station_id: str, prefix: str) -> None:
    station = env.station_index[station_id]
    result = env._current_station_pricing_result(station_id)
    estimated_cost = round(result.dynamic_price_per_kwh * 20.0, 3)
    print(prefix)
    print(f"  station_id: {station.station_id}")
    print(f"  transformer_id: {station.transformer_id}")
    print(f"  base_price_per_kwh: {round(result.base_price_per_kwh, 4)}")
    print(f"  dynamic_price_per_kwh: {round(result.dynamic_price_per_kwh, 4)}")
    print(f"  transformer_load_ratio: {round(result.load_ratio, 4)}")
    print(f"  headroom_ratio: {round(result.headroom_ratio, 4)}")
    print(f"  pricing_reason: {result.reason}")
    print(f"  estimated_cost_gbp_for_20kwh: {estimated_cost}")


def main() -> int:
    manager = RuntimeManager(
        REPO_ROOT,
        config=RuntimeConfig(dynamic_pricing_enabled=True, recommendation_policy_name="cheapest"),
    )
    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    baseline = manager.recommend(request_payload("dynamic-pricing-baseline"), recommendation_policy_name="cheapest")
    if baseline.top_recommendation is None:
        print("No baseline recommendation was produced.")
        return 1

    print("Dynamic pricing verification")
    print_option("Baseline top recommendation", baseline.top_recommendation)

    env = manager._load_env()
    station_ids = sorted(env.station_index)
    stressed_station_id = baseline.top_recommendation.station_id
    if len(station_ids) > 1:
        for candidate_station_id in station_ids:
            if env.station_index[candidate_station_id].transformer_id != baseline.top_recommendation.transformer_id:
                stressed_station_id = candidate_station_id
                break

    stressed_station = env.station_index[stressed_station_id]
    print_station_pricing(env, stressed_station.station_id, "Stressed-station pricing before added load")
    session_id = "verify_dynamic_pricing_stress_session"
    env.active_sessions[session_id] = ActiveChargingSession(
        request_id=session_id,
        station_id=stressed_station.station_id,
        transformer_id=stressed_station.transformer_id,
        started_at=env.current_time,
        expected_completion_ts=env.current_time + timedelta(minutes=45),
        assigned_power_kw=max(stressed_station.station_capacity_kw_assumed * 0.75, 50.0),
        estimated_cost_gbp=0.0,
    )
    env.stations_runtime[stressed_station.station_id].active_session_ids.append(session_id)
    print_station_pricing(env, stressed_station.station_id, "Stressed-station pricing after added load")
    manager._persist_env(env, include_events=False)

    stressed = manager.recommend(request_payload("dynamic-pricing-stressed"), recommendation_policy_name="cheapest")
    if stressed.top_recommendation is None:
        print("No stressed recommendation was produced.")
        return 1

    print_option(
        f"Post-stress top recommendation (stressed transformer {stressed_station.transformer_id})",
        stressed.top_recommendation,
    )
    if stressed.alternatives:
        print_option("First alternative after stress", stressed.alternatives[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
