"""Placeholder entry point for ACN dataset cleaning."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the ACN cleaning job."""

    parser = argparse.ArgumentParser(description="Clean raw ACN EV charging data.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw/acn"))
    parser.add_argument("--output-path", type=Path, default=Path("data/interim/acn_cleaned.parquet"))
    return parser


def main() -> int:
    """Run the placeholder CLI."""

    args = build_parser().parse_args()
    _ = args
    # TODO: implement ACN data cleaning.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
