from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/digital_twin/verify_runtime_liveness.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "digital_twin" / "verify_runtime_liveness.py"
    runpy.run_path(str(target), run_name="__main__")
