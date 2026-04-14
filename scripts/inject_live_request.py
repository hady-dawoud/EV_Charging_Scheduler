"""Inject a standalone live-style charging request into the Dundee runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.demo import build_sample_request  # noqa: E402
from services.sim_runtime.runtime_manager import RuntimeManager  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inject a live-style request into the Dundee runtime.")
    parser.add_argument("--payload-file", type=Path)
    parser.add_argument("--sample", action="store_true", default=False)
    return parser


def load_payload(payload_file: Path | None, sample: bool) -> dict:
    if sample or payload_file is None:
        return build_sample_request().model_dump(mode="json")
    return json.loads(payload_file.read_text(encoding="utf-8"))


def main() -> None:
    args = build_parser().parse_args()
    runtime = RuntimeManager(REPO_ROOT)
    payload = load_payload(args.payload_file, args.sample)
    response = runtime.inject_request(payload)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
