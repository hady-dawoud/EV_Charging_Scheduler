from __future__ import annotations

from pathlib import Path
import runpy

# Backward-compatible entrypoint.
# Wrapper target: scripts/rl_training/verify_offline_rl_training_env.py
if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "rl_training" / "verify_offline_rl_training_env.py"
    runpy.run_path(str(target), run_name="__main__")
