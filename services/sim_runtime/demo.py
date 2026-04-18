"""Demo helpers for the standalone Dundee simulator runtime."""

from __future__ import annotations

from typing import Any

from ev_core.contracts.requests import ExternalChargingRequest

from .runtime_manager import RuntimeManager

SAMPLE_EXTERNAL_REQUEST: dict[str, Any] = {
    "client_request_id": "demo-mobile-001",
    "request_timestamp": "2024-06-10T17:30:00+00:00",
    "current_latitude": 56.4620,
    "current_longitude": -2.9707,
    "target_soc": 80,
    "current_soc": 35,
    "battery_kwh": 60,
    "preference_mode": "fastest",
    "charger_type": "dc",
    "latest_finish_ts": "2024-06-10T20:00:00+00:00",
}

BUSY_AFTERNOON_DEMO: dict[str, Any] = {
    "replay_day": "2024-06-10",
    "start_hour": 15,
    "start_minute": 0,
    "policy_mode": "overload_aware",
    "runtime_mode": "hybrid",
    "demand_multiplier": 1.35,
    "warm_start_hours": 4,
}


def build_sample_request() -> ExternalChargingRequest:
    """Return the sample external-style request used by local demo tooling."""

    return ExternalChargingRequest.model_validate(SAMPLE_EXTERNAL_REQUEST)


def run_demo_day(runtime: RuntimeManager, *, replay_day: str = "2024-06-10", ticks: int = 12) -> None:
    """Start the runtime for a Dundee replay day and advance a short demo window."""

    runtime.start(replay_day=replay_day)
    runtime.tick(steps=max(ticks, 1))


def run_busy_afternoon_demo(runtime: RuntimeManager, *, ticks: int = 12) -> None:
    """Start the Busy Afternoon Dundee preset and advance a short demo window."""

    runtime.start(**BUSY_AFTERNOON_DEMO)
    runtime.tick(steps=max(ticks, 1))
