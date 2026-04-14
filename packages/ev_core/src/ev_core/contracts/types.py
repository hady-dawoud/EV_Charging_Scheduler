"""Shared type aliases for the standalone EV-core scaffolding."""

from __future__ import annotations

from typing import Literal, NewType

StationId = NewType("StationId", str)
ConnectorId = NewType("ConnectorId", str)
VehicleId = NewType("VehicleId", str)
RequestId = NewType("RequestId", str)
TimeStepIndex = NewType("TimeStepIndex", int)

TimeResolutionMinutes = Literal[15]
DEFAULT_TIME_RESOLUTION_MINUTES: TimeResolutionMinutes = 15

__all__ = [
    "ConnectorId",
    "DEFAULT_TIME_RESOLUTION_MINUTES",
    "RequestId",
    "StationId",
    "TimeResolutionMinutes",
    "TimeStepIndex",
    "VehicleId",
]
