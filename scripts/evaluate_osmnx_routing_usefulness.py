from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/maps/evaluate_osmnx_routing_usefulness.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "maps" / "evaluate_osmnx_routing_usefulness.py"
    runpy.run_path(str(target), run_name="__main__")
