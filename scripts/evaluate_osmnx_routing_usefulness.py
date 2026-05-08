"""Evaluate whether optional OSMnx routing is useful enough to keep for later work."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import statistics
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.routing.osmnx_provider import OSMnxRoutingProvider
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


GRAPH_PATH = REPO_ROOT / "data" / "processed" / "routing" / "dundee_drive.graphml"


def main() -> int:
    if not GRAPH_PATH.exists():
        print("Run scripts/build_dundee_osmnx_graph.py first")
        return 0

    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    generator = SyntheticLiveRequestGenerator(
        request_generator_params=bundle.request_generator_params,
        stations=bundle.stations.to_dict(orient="records"),
        seed="osmnx-usefulness-eval",
    )
    simple_provider = SimpleDistanceRoutingProvider()
    osmnx_provider = OSMnxRoutingProvider(graph_path=GRAPH_PATH)
    requests = generator.generate_batch(
        start_ts=datetime(2024, 6, 10, 12, 0),
        end_ts=datetime(2024, 6, 10, 13, 0),
        count=8,
    )
    stations = [bundle.stations.iloc[index] for index in range(min(8, len(bundle.stations)))]

    total_routes = 0
    osmnx_successes = 0
    fallback_count = 0
    suspicious_count = 0
    ratios: list[float] = []
    fallback_reasons: dict[str, int] = {}
    suspicious_examples: list[str] = []

    for request in requests:
        for station in stations:
            total_routes += 1
            simple_estimate = simple_provider.estimate_route(request, station)
            osmnx_estimate = osmnx_provider.estimate_route(request, station)
            metadata = osmnx_estimate.metadata or {}
            fallback_used = bool(metadata.get("fallback_used"))
            if fallback_used:
                fallback_count += 1
                reason = str(metadata.get("fallback_reason") or "unknown")
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
                suspicious_count += 1
                if len(suspicious_examples) < 5:
                    suspicious_examples.append(
                        f"fallback station={station['station_id']} request={request.request_id} reason={reason}"
                    )
                continue

            osmnx_successes += 1
            ratio = osmnx_estimate.distance_km / max(simple_estimate.distance_km, 0.001)
            ratios.append(ratio)
            if ratio < 0.8:
                suspicious_count += 1
                if len(suspicious_examples) < 5:
                    suspicious_examples.append(
                        f"shorter_than_simple station={station['station_id']} request={request.request_id} ratio={ratio:.3f}"
                    )
            elif ratio > 3.0:
                suspicious_count += 1
                if len(suspicious_examples) < 5:
                    suspicious_examples.append(
                        f"much_longer_than_simple station={station['station_id']} request={request.request_id} ratio={ratio:.3f}"
                    )
            elif osmnx_estimate.duration_minutes is None:
                suspicious_count += 1
                if len(suspicious_examples) < 5:
                    suspicious_examples.append(
                        f"missing_duration station={station['station_id']} request={request.request_id}"
                    )

    success_rate = (osmnx_successes / total_routes) if total_routes else 0.0
    fallback_rate = (fallback_count / total_routes) if total_routes else 0.0
    median_ratio = statistics.median(ratios) if ratios else 0.0
    useful_for_rl = (
        GRAPH_PATH.exists()
        and success_rate >= 0.95
        and fallback_rate <= 0.05
        and suspicious_count == 0
    )

    print("OSMnx routing usefulness evaluation")
    print(f"routes_tested: {total_routes}")
    print(f"osmnx_success_rate: {success_rate:.3f}")
    print(f"fallback_rate: {fallback_rate:.3f}")
    print(f"median_ratio: {median_ratio:.3f}")
    print(f"suspicious_route_count: {suspicious_count}")
    print(f"fallback_reasons: {fallback_reasons}")
    print(f"suspicious_examples: {suspicious_examples}")
    print(f"verdict: {'useful_for_rl_later' if useful_for_rl else 'optional_only_for_now'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
