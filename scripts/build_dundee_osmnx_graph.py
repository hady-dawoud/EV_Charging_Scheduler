"""Build a cached Dundee drive graph for optional OSMnx routing."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GRAPH_PATH = REPO_ROOT / "data" / "processed" / "routing" / "dundee_drive.graphml"
PLACE_QUERY = "Dundee, Scotland, United Kingdom"


def main() -> int:
    import osmnx as ox

    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Building OSMnx drive graph for: {PLACE_QUERY}")
    graph = ox.graph_from_place(PLACE_QUERY, network_type="drive")
    ox.save_graphml(graph, GRAPH_PATH)
    print(f"Saved graph to: {GRAPH_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
