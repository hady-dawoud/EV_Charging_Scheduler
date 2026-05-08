"""Verify optional OSMnx routing against the Dundee dataset when a graph exists."""

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
from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.routing.osmnx_provider import OSMnxRoutingProvider


GRAPH_PATH = REPO_ROOT / "data" / "processed" / "routing" / "dundee_drive.graphml"


def request_payload() -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id="osmnx-routing-check",
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.970,
        requested_energy_kwh=20.0,
        preference_mode="closest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id="osmnx-routing-check",
        zone_id="zone_central_waterfront",
    )


def main() -> int:
    if not GRAPH_PATH.exists():
        print("Run scripts/build_dundee_osmnx_graph.py first")
        return 0

    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    station_row = bundle.stations.iloc[0]
    provider = OSMnxRoutingProvider(graph_path=GRAPH_PATH)
    request = request_payload()
    estimate = provider.estimate_route(request, station_row)
    metadata = estimate.metadata or {}

    print("OSMnx routing provider verification")
    print(f"provider: {estimate.provider}")
    print(f"fallback_used: {metadata.get('fallback_used')}")
    print(f"origin: ({request.current_latitude}, {request.current_longitude})")
    print(f"destination: ({station_row['latitude']}, {station_row['longitude']})")
    print(f"station_id: {station_row['station_id']}")
    print(f"station_name: {station_row['station_name']}")
    print(f"distance_km: {round(estimate.distance_km, 4)}")
    print(f"duration_minutes: {None if estimate.duration_minutes is None else round(estimate.duration_minutes, 2)}")
    print(f"graph_path: {metadata.get('graph_path', str(GRAPH_PATH))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
