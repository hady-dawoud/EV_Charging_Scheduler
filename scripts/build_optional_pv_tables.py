from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/forecasting/build_optional_pv_tables.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "forecasting" / "build_optional_pv_tables.py"
    runpy.run_path(str(target), run_name="__main__")
