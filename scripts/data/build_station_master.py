"""Placeholder entry point for station master table creation."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for station master generation."""

    parser = argparse.ArgumentParser(description="Build the station master reference table.")
    parser.add_argument("--output-path", type=Path, default=Path("data/processed/station_master.parquet"))
    return parser


def main() -> int:
    """Run the placeholder CLI."""

    args = build_parser().parse_args()
    _ = args
    # TODO: implement station master generation.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
