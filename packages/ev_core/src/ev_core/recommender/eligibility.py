"""Station access eligibility rules for recommendation candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StationEligibilityResult:
    eligible: bool
    reason: str | None = None


class StationEligibilityFilter:
    """Apply station access flags before recommendation candidate scoring."""

    def is_eligible(self, station: Any, request: Any) -> StationEligibilityResult:
        metadata = getattr(request, "metadata", {}) or {}

        if getattr(station, "exclude_from_recommendations", False):
            return StationEligibilityResult(False, "excluded_from_recommendations")
        if not getattr(station, "is_public", True) and not bool(metadata.get("allow_non_public_stations", False)):
            return StationEligibilityResult(False, "non_public")
        if getattr(station, "is_fleet_only", False) and not bool(metadata.get("allow_fleet_only", False)):
            return StationEligibilityResult(False, "fleet_only")
        if getattr(station, "requires_membership", False) and not bool(metadata.get("allow_membership_sites", False)):
            return StationEligibilityResult(False, "requires_membership")
        return StationEligibilityResult(True)


__all__ = ["StationEligibilityFilter", "StationEligibilityResult"]
