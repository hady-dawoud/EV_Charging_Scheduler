"""Preprocessing placeholders for request, station, and time-series cleaning."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CleaningContext:
    """Metadata shared by future cleaning jobs on the 15-minute time base."""

    source_name: str
    resolution_minutes: int = 15
    timezone: str = "UTC"


def clean_frame(frame: pd.DataFrame, context: CleaningContext) -> pd.DataFrame:
    """Clean a raw frame once source-specific rules are finalized."""

    raise NotImplementedError("TODO: implement source-specific cleaning steps.")
