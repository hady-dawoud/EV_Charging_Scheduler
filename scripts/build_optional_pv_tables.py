"""Placeholder entry point for optional PV feature tables."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for optional PV table generation."""

    parser = argparse.ArgumentParser(description="Build optional PV-related feature tables.")
    parser.add_argument("--output-path", type=Path, default=Path("data/processed/pv_15min.parquet"))
    return parser


def main() -> int:
    """Run the placeholder CLI."""

    args = build_parser().parse_args()
    _ = args
    # TODO: implement optional PV table generation.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
