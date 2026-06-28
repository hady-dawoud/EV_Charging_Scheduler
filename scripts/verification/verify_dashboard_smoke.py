"""Verify dashboard data helpers can read a freshly-started runtime state."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboards.sim_dashboard.app import build_status_panel_values, load_runtime_data
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationOption, RecommendationResponse
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def write_fallback_history(storage: RuntimeStorage) -> None:
    request_time = datetime.fromisoformat("2024-06-10T15:00:00")
    external_request = ExternalChargingRequest(
        client_request_id="mobile-dashboard-smoke",
        request_timestamp=request_time,
        current_latitude=56.462,
        current_longitude=-2.9707,
        requested_energy_kwh=24.0,
        preference_mode="fastest",
        charger_type="Any",
        latest_finish_ts=request_time + timedelta(minutes=90),
        metadata={
            "selected_location_name": "Central Dundee",
            "user_id": "smoke-user",
        },
    )
    recommendation = RecommendationResponse(
        request_id="external-dashboard-smoke",
        client_request_id="mobile-dashboard-smoke",
        simulated_timestamp=request_time,
        zone_id="zone_central_waterfront",
        top_recommendation=RecommendationOption(
            station_id="greenmarket_150kw_bus_charger",
            station_name="Greenmarket 150kW Bus Charger",
            zone_id="zone_central_waterfront",
            transformer_id="tx_central_market",
            score=0.91,
            distance_km=0.5,
            estimated_wait_minutes=0,
            estimated_duration_minutes=15,
            estimated_cost_gbp=18.4,
            transformer_headroom_kw=220.0,
            current_queue=0,
            utilization=0.5,
            charger_compatible=True,
            reason_tags=["low_wait"],
            metadata={
                "rl_safety_status": "safe",
                "rl_safety_score": 0.88,
                "grid_truth_level": "area_pf",
            },
        ),
        metadata={"effective_policy_name": "rl_safety_preference"},
    )
    storage.artifacts.latest_external_requests_path.write_text(
        external_request.model_dump_json(indent=2).join(["[\n", "\n]\n"]),
        encoding="utf-8",
    )
    storage.artifacts.recent_recommendations_path.write_text(
        recommendation.model_dump_json(indent=2).join(["[\n", "\n]\n"]),
        encoding="utf-8",
    )


def main() -> int:
    storage_root = REPO_ROOT / "outputs" / "test_runtime" / f"verify_dashboard_{uuid4().hex}"
    manager = RuntimeManager(REPO_ROOT)
    manager.storage = RuntimeStorage(storage_root)
    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    write_fallback_history(manager.storage)

    _, state, metrics, metric_history, recommendations, external_requests, events, status = load_runtime_data(storage_root)
    if state is None or metrics is None:
        print("FAIL: dashboard could not load fresh runtime state and metrics")
        return 1
    summary = build_status_panel_values(state, metrics, status)
    required = [
        "runtime_status",
        "simulated_timestamp",
        "recommendation_policy",
        "pricing_model",
        "dynamic_pricing_enabled",
        "routing_provider",
        "osmnx_graph_exists",
    ]
    missing = [field for field in required if field not in summary]
    if missing:
        print(f"FAIL: dashboard status summary missing {missing}")
        return 1
    if not recommendations or not external_requests:
        print("FAIL: dashboard did not load typed request/response fallback history")
        return 1
    if recommendations[0].client_request_id != external_requests[0].client_request_id:
        print("FAIL: fallback request/response client_request_id values do not match")
        return 1

    print("Dashboard smoke verification")
    print(f"runtime_status: {summary['runtime_status']}")
    print(f"simulated_timestamp: {summary['simulated_timestamp']}")
    print(f"recommendation_policy: {summary['recommendation_policy']}")
    print(f"pricing_model: {summary['pricing_model']}")
    print(f"dynamic_pricing_enabled: {summary['dynamic_pricing_enabled']}")
    print(f"routing_provider: {summary['routing_provider']}")
    print(f"osmnx_graph_exists: {summary['osmnx_graph_exists']}")
    print(f"metric_history_count: {len(metric_history)}")
    print(f"recent_recommendations_count: {len(recommendations)}")
    print(f"external_requests_count: {len(external_requests)}")
    print(f"fallback_client_request_id: {external_requests[0].client_request_id}")
    print(f"events_count: {len(events)}")
    print("PASS: dashboard helpers loaded runtime storage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
