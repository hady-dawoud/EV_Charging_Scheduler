"""Verify synthetic-live requests through the runtime recommendation path."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from services.sim_runtime.runtime_manager import RuntimeManager
from services.sim_runtime.storage import RuntimeStorage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify synthetic-live generated requests against runtime recommendations.")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--timestamp", type=str, default="2024-06-10T12:00:00")
    parser.add_argument("--seed", type=str, default="synthetic-live-verify")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    generator = SyntheticLiveRequestGenerator(
        request_generator_params=bundle.request_generator_params,
        stations=bundle.stations.to_dict(orient="records"),
        seed=args.seed,
    )
    manager = RuntimeManager(REPO_ROOT)
    manager.storage = RuntimeStorage(REPO_ROOT / "outputs" / "test_runtime" / f"synthetic_live_verify_{uuid4().hex}")
    state = manager.start(replay_day="2024-06-10", start_hour=12, start_minute=0, warm_start_hours=0)
    station_ids = {station.station_id for station in state.stations}

    timestamp = datetime.fromisoformat(args.timestamp)
    print("Synthetic-live runtime verification")
    print(f"Stations: {len(station_ids)}")
    for index in range(1, args.count + 1):
        request = generator.generate_one(timestamp, index=index)
        response = manager.recommend(request)
        top = response.top_recommendation
        print(f"{request.request_id}: {top.station_id if top else 'none'}")
        if top is None or top.station_id not in station_ids:
            print(f"Synthetic-live runtime verification failed for {request.request_id}.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
