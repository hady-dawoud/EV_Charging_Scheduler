"""Schemas and type aliases shared across future EV-core modules."""

from .schemas import ChargingRequest, RecommendationCandidate, StationSnapshot, TimeWindow
from .types import DEFAULT_TIME_RESOLUTION_MINUTES, TimeResolutionMinutes

__all__ = [
    "ChargingRequest",
    "DEFAULT_TIME_RESOLUTION_MINUTES",
    "RecommendationCandidate",
    "StationSnapshot",
    "TimeResolutionMinutes",
    "TimeWindow",
]
