from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/data/build_dundee_qc_and_plots.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "data" / "build_dundee_qc_and_plots.py"
    runpy.run_path(str(target), run_name="__main__")
