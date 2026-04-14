"""Placeholder entry point for request seed table generation."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for request seed generation."""

    parser = argparse.ArgumentParser(description="Build the request seed table.")
    parser.add_argument("--output-path", type=Path, default=Path("data/processed/request_seed_table.parquet"))
    return parser


def main() -> int:
    """Run the placeholder CLI."""

    args = build_parser().parse_args()
    _ = args
    # TODO: implement request seed table generation.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
