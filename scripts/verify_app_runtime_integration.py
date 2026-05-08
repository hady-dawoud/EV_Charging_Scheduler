"""Verify the app-facing runtime path exposes the active pricing and routing metadata."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.contracts.requests import ExternalChargingRequest
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def request_payload() -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id="app-runtime-integration",
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.9707,
        target_soc=80.0,
        current_soc=45.0,
        battery_kwh=82.0,
        requested_energy_kwh=28.7,
        preference_mode="cheapest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id="app-runtime-integration",
        zone_id="zone_central_waterfront",
        metadata={"channel": "mobile-app"},
    )


def main() -> int:
    routing_provider_name = os.getenv("ROUTING_PROVIDER_NAME", "simple_distance")
    osmnx_graph_path = os.getenv("OSMNX_GRAPH_PATH", "data/processed/routing/dundee_drive.graphml")
    manager = RuntimeManager(
        REPO_ROOT,
        config=RuntimeConfig(
            dynamic_pricing_enabled=True,
            routing_provider_name=routing_provider_name,
            osmnx_graph_path=osmnx_graph_path,
        ),
    )
    manager.storage = RuntimeStorage(REPO_ROOT / "outputs" / "test_runtime" / f"app_runtime_verify_{uuid4().hex}")
    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    response = manager.recommend(request_payload())
    status = manager.get_runtime_status()

    top = response.top_recommendation
    if top is None:
        print("No top recommendation was produced.")
        return 1
    metadata = top.metadata or {}
    required_metadata_fields = [
        "tariff_class",
        "base_price_per_kwh",
        "final_price_per_kwh",
        "total_dynamic_multiplier",
        "transformer_multiplier",
        "congestion_multiplier",
        "selected_connector_type",
        "selected_connector_power_kw",
        "effective_power_kw",
        "routing_provider_name",
    ]
    missing_metadata = [field for field in required_metadata_fields if field not in metadata]
    if top.estimated_cost_gbp <= 0.0 or missing_metadata:
        print(f"Recommendation metadata missing or invalid: {missing_metadata}")
        return 1

    required_status_fields = [
        "pricing_model",
        "dynamic_pricing_enabled",
        "routing_provider_name",
        "routing_provider_available",
        "osmnx_graph_path",
        "osmnx_graph_exists",
        "recommendation_policy_name",
    ]
    missing_status = [field for field in required_status_fields if field not in status]
    if missing_status:
        print(f"Runtime status missing fields: {missing_status}")
        return 1

    print("App runtime integration verification")
    print(f"top_station_id: {top.station_id}")
    print(f"estimated_cost_gbp: {round(top.estimated_cost_gbp, 3)}")
    print(f"tariff_class: {metadata['tariff_class']}")
    print(f"final_price_per_kwh: {metadata['final_price_per_kwh']}")
    print(f"routing_provider_name: {metadata['routing_provider_name']}")
    print(f"runtime_status: {status}")

    if routing_provider_name == "osmnx" and bool(status.get("osmnx_graph_exists")):
        all_options = [response.top_recommendation, *response.alternatives]
        if not any(not bool((option.metadata or {}).get("routing_fallback_used", True)) for option in all_options if option is not None):
            print(f"OSMnx was requested but all routes fell back. last_reason={status.get('last_routing_fallback_reason')}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
