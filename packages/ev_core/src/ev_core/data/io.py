"""Lightweight IO helpers for standalone EV-core datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read a CSV dataset into a DataFrame."""

    return pd.read_csv(Path(path), **kwargs)


def write_csv(frame: pd.DataFrame, path: str | Path, **kwargs) -> None:
    """Write a DataFrame to CSV with parent creation."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False, **kwargs)
