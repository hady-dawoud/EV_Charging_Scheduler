"""Placeholder entry point for transformer-to-station mapping."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for transformer mapping generation."""

    parser = argparse.ArgumentParser(description="Build the transformer to station map.")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("data/processed/transformer_station_map.parquet"),
    )
    return parser


def main() -> int:
    """Run the placeholder CLI."""

    args = build_parser().parse_args()
    _ = args
    # TODO: implement transformer to station mapping.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
