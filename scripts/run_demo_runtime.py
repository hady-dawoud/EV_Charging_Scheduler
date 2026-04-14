"""Run a short standalone Dundee simulator demo outside apps/**."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.demo import run_demo_day  # noqa: E402
from services.sim_runtime.runtime_manager import RuntimeManager  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the standalone Dundee simulator demo.")
    parser.add_argument("--day", default="2024-06-10")
    parser.add_argument("--ticks", type=int, default=12)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    runtime = RuntimeManager(REPO_ROOT)
    run_demo_day(runtime, replay_day=args.day, ticks=args.ticks)
    state = runtime.get_latest_state()
    if state is not None:
        print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
