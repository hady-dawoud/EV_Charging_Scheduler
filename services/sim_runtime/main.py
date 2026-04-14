"""CLI entry point for the standalone Dundee simulator runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo import build_sample_request
from .runtime_manager import RuntimeManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone Dundee simulator runtime.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a fresh Dundee replay runtime.")
    start.add_argument("--day", default="2024-06-10")
    start.add_argument("--hour", type=int, default=0)
    start.add_argument("--minute", type=int, default=0)
    start.add_argument("--policy", default="overload_aware")
    start.add_argument("--mode", default="replay", choices=["replay", "synthetic", "hybrid"])
    start.add_argument("--demand-multiplier", type=float, default=1.0)
    start.add_argument("--warm-start-hours", type=int, default=0)
    start.add_argument("--preset", choices=["busy_afternoon"])
    start.add_argument("--loop", action="store_true")
    start.add_argument("--interval-seconds", type=float, default=1.0)

    reset = subparsers.add_parser("reset", help="Reset the Dundee runtime.")
    reset.add_argument("--day", default="2024-06-10")
    reset.add_argument("--hour", type=int, default=0)
    reset.add_argument("--minute", type=int, default=0)
    reset.add_argument("--policy", default="overload_aware")
    reset.add_argument("--mode", default="replay", choices=["replay", "synthetic", "hybrid"])
    reset.add_argument("--demand-multiplier", type=float, default=1.0)
    reset.add_argument("--warm-start-hours", type=int, default=0)
    reset.add_argument("--preset", choices=["busy_afternoon"])

    tick = subparsers.add_parser("tick", help="Advance the runtime by one or more 15-minute steps.")
    tick.add_argument("--steps", type=int, default=1)

    subparsers.add_parser("pause", help="Pause the Dundee runtime.")
    subparsers.add_parser("stop-loop", help="Stop the continuous ticking loop.")
    subparsers.add_parser("state", help="Print the latest state snapshot.")
    subparsers.add_parser("metrics", help="Print the latest metrics snapshot.")
    subparsers.add_parser("status", help="Print the latest runtime liveness status.")

    inject = subparsers.add_parser("inject", help="Inject an external-style request into the runtime.")
    inject.add_argument("--payload-file", type=Path)
    inject.add_argument("--sample", action="store_true")
    return parser


def load_payload(payload_file: Path | None, sample: bool) -> dict:
    if sample or payload_file is None:
        return build_sample_request().model_dump(mode="json")
    return json.loads(payload_file.read_text(encoding="utf-8"))


def main() -> None:
    args = build_parser().parse_args()
    runtime = RuntimeManager()

    if args.command == "start":
        snapshot = runtime.start(
            replay_day=args.day,
            start_hour=args.hour,
            start_minute=args.minute,
            policy_mode=args.policy,
            runtime_mode=args.mode,
            demand_multiplier=args.demand_multiplier,
            warm_start_hours=args.warm_start_hours,
            preset=args.preset,
        )
        print(snapshot.model_dump_json(indent=2))
        if args.loop:
            runtime.start_loop(interval_seconds=args.interval_seconds)
            try:
                runtime.wait_for_loop()
            except KeyboardInterrupt:
                runtime.stop_loop()
    elif args.command == "reset":
        snapshot = runtime.reset(
            replay_day=args.day,
            start_hour=args.hour,
            start_minute=args.minute,
            policy_mode=args.policy,
            runtime_mode=args.mode,
            demand_multiplier=args.demand_multiplier,
            warm_start_hours=args.warm_start_hours,
            preset=args.preset,
        )
        print(snapshot.model_dump_json(indent=2))
    elif args.command == "tick":
        snapshot = runtime.tick(steps=args.steps)
        print(snapshot.model_dump_json(indent=2))
    elif args.command == "pause":
        snapshot = runtime.pause()
        print(snapshot.model_dump_json(indent=2))
    elif args.command == "stop-loop":
        print(json.dumps(runtime.stop_loop(), indent=2))
    elif args.command == "state":
        snapshot = runtime.get_latest_state()
        print(snapshot.model_dump_json(indent=2) if snapshot is not None else "{}")
    elif args.command == "metrics":
        metrics = runtime.get_latest_metrics()
        print(metrics.model_dump_json(indent=2) if metrics is not None else "{}")
    elif args.command == "status":
        print(json.dumps(runtime.get_runtime_status(), indent=2))
    elif args.command == "inject":
        payload = load_payload(args.payload_file, args.sample)
        response = runtime.inject_request(payload)
        print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
