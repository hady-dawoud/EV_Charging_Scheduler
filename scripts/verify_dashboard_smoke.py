"""Verify dashboard data helpers can read a freshly-started runtime state."""

from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboards.sim_dashboard.app import build_status_panel_values, load_runtime_data
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def main() -> int:
    storage_root = REPO_ROOT / "outputs" / "test_runtime" / f"verify_dashboard_{uuid4().hex}"
    manager = RuntimeManager(REPO_ROOT)
    manager.storage = RuntimeStorage(storage_root)
    manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)

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
    print(f"events_count: {len(events)}")
    print("PASS: dashboard helpers loaded runtime storage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
