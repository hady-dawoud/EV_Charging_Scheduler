"""Export a manual-inspection route preview from the optional Dundee OSMnx graph."""

from __future__ import annotations

import json
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
OUTPUT_PATH = REPO_ROOT / "outputs" / "runtime" / "osmnx_route_preview.geojson"


def request_payload() -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id="osmnx-route-preview",
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        current_latitude=56.462,
        current_longitude=-2.970,
        requested_energy_kwh=20.0,
        preference_mode="closest",
        charger_type="Any",
        latest_finish_ts=datetime(2024, 6, 10, 15, 0),
        source_type="external_live",
        request_id="osmnx-route-preview",
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
    if metadata.get("fallback_used"):
        print(
            "OSMnx route preview could not be exported because the provider fell back. "
            f"reason={metadata.get('fallback_reason')}"
        )
        return 1

    graph = provider._load_graph()
    route_nodes = metadata.get("route_nodes", [])
    coordinates = [[float(graph.nodes[node]["x"]), float(graph.nodes[node]["y"])] for node in route_nodes]
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "provider": estimate.provider,
                    "station_id": station_row["station_id"],
                    "station_name": station_row["station_name"],
                    "distance_km": estimate.distance_km,
                    "duration_minutes": estimate.duration_minutes,
                    "graph_path": metadata.get("graph_path", str(GRAPH_PATH)),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
            }
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    print(f"Route preview written to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
