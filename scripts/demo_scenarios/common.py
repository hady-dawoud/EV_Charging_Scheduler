from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any


API_BASE = os.environ.get("DEMO_API_BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("DEMO_AUTH_TOKEN")


def api_url(path: str) -> str:
    return f"{API_BASE}/{path.lstrip('/')}"


def read_json(response: Any) -> Any:
    raw = response.read().decode("utf-8")
    if not raw:
        return None
    return json.loads(raw)


def get_json(path: str) -> Any:
    request = urllib.request.Request(
        api_url(path),
        method="GET",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return read_json(response)


def post_json(path: str, payload: dict[str, Any], token: str | None = None) -> Any:
    token = token or TOKEN
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        api_url(path),
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return read_json(response)


def mobile_payload(preference_mode: str, connector_type: str = "Any") -> dict[str, Any]:
    battery_level = 35.0
    target_battery_level = 80.0
    battery_kwh = 64.0

    return {
        "client_request_id": f"demo_script_{preference_mode}_{int(time.time() * 1000)}",
        "latitude": 56.4590,
        "longitude": -2.9707,
        "battery_level": battery_level,
        "target_battery_level": target_battery_level,
        "battery_kwh": battery_kwh,
        "vehicle_max_ac_kw": 11.0,
        "vehicle_max_dc_kw": 150.0,
        "requested_energy_kwh": ((target_battery_level - battery_level) / 100.0) * battery_kwh,
        "preference_mode": preference_mode,
        "connector_type": connector_type,
        "latest_finish_minutes_from_now": 120,
        "zone_id": "zone_central_waterfront",
        "metadata": {
            "channel": "demo_script",
            "scenario": "preference_mode_comparison",
        },
    }


def option_meta(option: dict[str, Any] | None) -> dict[str, Any]:
    if not option:
        return {}
    metadata = option.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def print_top_summary(result: dict[str, Any]) -> None:
    top = result.get("top_recommendation") or {}
    meta = option_meta(top)
    response_meta = result.get("metadata") or {}

    print(json.dumps({
        "preference": response_meta.get("preference_mode"),
        "effective_policy": response_meta.get("effective_policy_name"),
        "top_station": top.get("station_name"),
        "score": top.get("score"),
        "cost_gbp": top.get("estimated_cost_gbp"),
        "distance_km": top.get("distance_km"),
        "wait_min": top.get("estimated_wait_minutes"),
        "duration_min": top.get("estimated_duration_minutes"),
        "final_price_per_kwh": meta.get("final_price_per_kwh"),
        "dynamic_multiplier": meta.get("total_dynamic_multiplier"),
        "rl_status": meta.get("rl_safety_status"),
        "rl_penalty": meta.get("rl_safety_penalty"),
        "rl_adjusted_score": meta.get("rl_safety_adjusted_score"),
    }, indent=2))
