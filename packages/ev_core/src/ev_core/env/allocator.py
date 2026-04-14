"""Allocation policies for the Dundee standalone simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ev_core.contracts.responses import RecommendationOption

from .entities import SimulationRequest


@dataclass(frozen=True)
class AllocationDecision:
    """Assignment decision for a single request on the 15-minute time base."""

    request_id: str
    station_id: str | None
    policy_mode: str
    score: float | None = None
    accepted: bool = True
    reason_tags: tuple[str, ...] = field(default_factory=tuple)


class AllocationPolicy(Protocol):
    """Protocol for choosing one recommendation option for a request."""

    def select_option(
        self,
        request: SimulationRequest,
        options: list[RecommendationOption],
    ) -> RecommendationOption | None:
        """Return the chosen recommendation option for the request."""
