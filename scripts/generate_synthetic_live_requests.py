"""Generate synthetic-live Dundee charging requests as JSONL."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic-live Dundee charging requests.")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--start", type=str, required=True, help="Start timestamp, for example 2024-06-10T12:00:00.")
    parser.add_argument("--end", type=str, required=True, help="End timestamp, for example 2024-06-10T18:00:00.")
    parser.add_argument("--seed", type=str, default="synthetic-live-cli")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "runtime" / "synthetic_live_requests.jsonl",
    )
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
    requests = generator.generate_batch(
        start_ts=datetime.fromisoformat(args.start),
        end_ts=datetime.fromisoformat(args.end),
        count=args.count,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for request in requests:
            handle.write(request.model_dump_json() + "\n")

    print(f"Wrote {len(requests)} synthetic-live requests to {args.output}")
    if requests:
        first = requests[0]
        print(
            "First request: "
            f"{first.request_id} | {first.zone_id} | {first.vehicle_profile_id} | "
            f"{first.preference_mode} | {first.charger_type}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
