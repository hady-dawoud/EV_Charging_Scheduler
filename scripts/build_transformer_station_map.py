from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/data/build_transformer_station_map.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "data" / "build_transformer_station_map.py"
    runpy.run_path(str(target), run_name="__main__")
