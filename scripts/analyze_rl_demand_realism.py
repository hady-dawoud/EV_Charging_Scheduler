from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/rl_training/analyze_rl_demand_realism.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "rl_training" / "analyze_rl_demand_realism.py"
    runpy.run_path(str(target), run_name="__main__")
