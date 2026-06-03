from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/verification/verify_app_pricing_duration_alignment.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "verification" / "verify_app_pricing_duration_alignment.py"
    runpy.run_path(str(target), run_name="__main__")
