"""Allocation-policy placeholders for request-to-station decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .entities import Station, VehicleRequest


@dataclass(frozen=True)
class AllocationDecision:
    """A future assignment decision for one request and one planning interval."""

    request_id: str
    station_id: str
    assigned_power_kw: float | None = None
    accepted: bool = True


class AllocationPolicy(Protocol):
    """Protocol for future allocator implementations."""

    def allocate(
        self,
        requests: list[VehicleRequest],
        stations: list[Station],
    ) -> list[AllocationDecision]:
        """Return candidate decisions for the current 15-minute interval."""
