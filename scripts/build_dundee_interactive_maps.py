from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/maps/build_dundee_interactive_maps.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "maps" / "build_dundee_interactive_maps.py"
    runpy.run_path(str(target), run_name="__main__")
