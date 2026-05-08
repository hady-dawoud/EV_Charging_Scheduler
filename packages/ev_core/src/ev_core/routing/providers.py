"""Routing provider contracts for recommendation distance estimation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RouteEstimate:
    """Lightweight route estimate returned by routing providers."""

    distance_km: float
    duration_minutes: float | None = None
    provider: str = "unknown"
    metadata: dict[str, Any] | None = None


class RoutingProvider(Protocol):
    """Dependency-light routing provider interface."""

    name: str

    def estimate_route(self, request: Any, station: Any) -> RouteEstimate:
        """Return a routing estimate between a request origin and a station."""

    def is_available(self) -> bool:
        """Return whether the provider appears usable in the current environment."""


__all__ = ["RouteEstimate", "RoutingProvider"]
