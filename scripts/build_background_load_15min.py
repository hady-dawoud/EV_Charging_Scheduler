"""Placeholder entry point for 15-minute background load tables."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for background load generation."""

    parser = argparse.ArgumentParser(description="Build 15-minute background load tables.")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("data/processed/background_load_15min.parquet"),
    )
    return parser


def main() -> int:
    """Run the placeholder CLI."""

    args = build_parser().parse_args()
    _ = args
    # TODO: implement 15-minute background load generation.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
