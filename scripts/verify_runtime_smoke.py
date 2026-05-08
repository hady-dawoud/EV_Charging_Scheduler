"""Run a lightweight Dundee runtime recommendation smoke check."""

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


POLICIES = ("weighted_score", "closest", "cheapest", "fastest", "overload_aware")


def request_payload() -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id="runtime-smoke",
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.970,
        requested_energy_kwh=20.0,
        preference_mode="closest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id="runtime-smoke-request",
        zone_id="zone_central_waterfront",
    )


def main() -> int:
    manager = RuntimeManager(REPO_ROOT)
    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    print("Runtime smoke verification")
    print(f"Stations: {len(state.stations)}")
    print(f"Transformers: {len(state.transformers)}")

    if not state.stations or not state.transformers:
        print("Runtime state is missing stations or transformers.")
        return 1

    station_ids = {station.station_id for station in state.stations}
    response = manager.inject_request(request_payload())
    top = response.top_recommendation
    print(f"Default policy top recommendation: {top.station_id if top else 'none'}")
    if top is None or top.station_id not in station_ids or len(response.alternatives) > 3:
        print("Default runtime recommendation smoke check failed.")
        return 1
    if not manager.get_recent_recommendations(limit=1):
        print("Runtime recommendation was not persisted.")
        return 1

    for policy in POLICIES:
        policy_response = manager.recommend(request_payload(), recommendation_policy_name=policy)
        policy_top = policy_response.top_recommendation
        print(f"{policy}: {policy_top.station_id if policy_top else 'none'}")
        if policy_top is None or policy_top.station_id not in station_ids:
            print(f"Policy sweep failed for {policy}.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
