"""Verify the default routing provider used by Dundee recommendations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.contracts.requests import ExternalChargingRequest
from services.sim_runtime.runtime_manager import RuntimeManager


def request_payload() -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id="routing-provider-check",
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.970,
        requested_energy_kwh=20.0,
        preference_mode="closest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id="routing-provider-check",
        zone_id="zone_central_waterfront",
    )


def main() -> int:
    manager = RuntimeManager(REPO_ROOT)
    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    env = manager._load_env()
    station = next(iter(env.station_index.values()), None)
    if station is None:
        print("No station was loaded into the runtime.")
        return 1

    request = request_payload()
    estimate = env.routing_provider.estimate_route(request, station)

    print("Routing provider verification")
    print(f"request_coordinates: ({request.current_latitude}, {request.current_longitude})")
    print(f"station_id: {station.station_id}")
    print(f"station_name: {station.station_name}")
    print(f"routing_provider: {env.routing_provider.name}")
    print(f"distance_km: {round(estimate.distance_km, 4)}")
    print(f"duration_minutes: {estimate.duration_minutes}")

    if env.routing_provider.name != "simple_distance":
        print("Unexpected default routing provider.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
