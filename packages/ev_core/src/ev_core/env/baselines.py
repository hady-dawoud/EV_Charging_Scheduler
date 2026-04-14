"""Baseline policy placeholders used for future benchmark comparisons."""

from __future__ import annotations

from .allocator import AllocationDecision, AllocationPolicy
from .entities import Station, VehicleRequest


class GreedyEarliestDeparturePolicy(AllocationPolicy):
    """Placeholder benchmark policy for future evaluation runs."""

    def allocate(
        self,
        requests: list[VehicleRequest],
        stations: list[Station],
    ) -> list[AllocationDecision]:
        raise NotImplementedError("TODO: implement a simple benchmark policy.")
