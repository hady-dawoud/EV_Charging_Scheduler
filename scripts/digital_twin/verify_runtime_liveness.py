"""Verify runtime keeps advancing and producing app-like recommendations."""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.contracts.requests import ExternalChargingRequest
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def app_like_request(manager: RuntimeManager, step: int) -> ExternalChargingRequest:
    state = manager.get_latest_state()
    if state is None:
        raise RuntimeError("Runtime state is not available.")
    request_ts = state.simulated_timestamp
    return ExternalChargingRequest(
        client_request_id=f"verify-liveness-client-{step}",
        request_timestamp=request_ts,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=20.0,
        preference_mode="Closest",
        charger_type="DC",
        latest_finish_ts=request_ts + timedelta(hours=3),
        source_type="external_live",
        request_id=f"verify-liveness-request-{step}",
        zone_id="zone_central_waterfront",
        vehicle_max_dc_kw=150.0,
        metadata={"channel": "verify_runtime_liveness"},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--start-hour", type=int, default=23)
    parser.add_argument("--start-minute", type=int, default=30)
    args = parser.parse_args()

    manager = RuntimeManager(REPO_ROOT)
    manager.storage = RuntimeStorage(REPO_ROOT / "outputs" / "test_runtime" / f"verify_liveness_{uuid4().hex}")
    manager.start(
        replay_day="2024-06-10",
        start_hour=args.start_hour,
        start_minute=args.start_minute,
        runtime_mode="replay",
        warm_start_hours=0,
    )

    no_feasible_count = 0
    previous_timestamp = None
    for step in range(max(args.steps, 1)):
        manager.tick(steps=1)
        state = manager.get_latest_state()
        if state is None:
            print("FAIL: runtime state disappeared")
            return 1
        response = manager.recommend(app_like_request(manager, step))
        top = response.top_recommendation
        if top is None:
            no_feasible_count += 1
        recent_count = len(manager.get_recent_recommendations(limit=100))
        status = manager.get_runtime_status()
        if previous_timestamp is not None and state.simulated_timestamp <= previous_timestamp:
            print("FAIL: runtime timestamp did not advance")
            return 1
        previous_timestamp = state.simulated_timestamp

        print(
            "step={step} simulated_timestamp={ts} active_sessions={active} queued_requests={queued} "
            "recent_recommendations={recent} top_station={top_station} no_feasible_count={no_feasible} "
            "runtime_status={runtime_status} current_policy={policy} routing_provider={routing} pricing_model={pricing} "
            "replay_exhausted={replay_exhausted} terminal_reason={terminal_reason}".format(
                step=step,
                ts=state.simulated_timestamp.isoformat(),
                active=status.get("active_session_count"),
                queued=status.get("queued_request_count"),
                recent=recent_count,
                top_station=None if top is None else top.station_id,
                no_feasible=no_feasible_count,
                runtime_status=status.get("runtime_status"),
                policy=status.get("recommendation_policy_name"),
                routing=status.get("routing_provider_name"),
                pricing=status.get("pricing_model"),
                replay_exhausted=status.get("replay_exhausted"),
                terminal_reason=status.get("terminal_reason"),
            )
        )

    if no_feasible_count:
        print(f"FAIL: {no_feasible_count} recommendation calls produced no feasible option")
        return 1
    print("PASS: runtime advanced and continued producing recommendations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
