"""Helpers for turning feasible Dundee candidates into station-level action masks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def build_station_action_mask(
    *,
    request: Any,
    stations: Sequence[Any],
    candidate_contexts: Sequence[Any],
) -> list[bool]:
    """Return a boolean mask aligned with the deterministic station list.

    Feasibility is inherited from the existing Dundee candidate builder. If a station
    appears in `candidate_contexts`, it is considered a valid action for the current
    request; otherwise it is invalid.
    """

    del request
    candidate_station_ids = {str(candidate.station_id) for candidate in candidate_contexts}
    return [str(station.station_id) in candidate_station_ids for station in stations]


__all__ = ["build_station_action_mask"]
