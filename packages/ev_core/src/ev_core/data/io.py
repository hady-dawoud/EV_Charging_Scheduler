"""Input/output helpers for future EV datasets and derived tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def resolve_path(path: str | Path) -> Path:
    """Return a normalized path object for future data-loading helpers."""

    return Path(path).expanduser().resolve()


def read_table(path: str | Path) -> pd.DataFrame:
    """Read a tabular dataset once source-specific formats are defined."""

    raise NotImplementedError("TODO: implement source-aware table readers.")


def write_table(frame: pd.DataFrame, path: str | Path) -> None:
    """Persist a tabular dataset using the agreed project storage format."""

    raise NotImplementedError("TODO: implement project-standard table writers.")
