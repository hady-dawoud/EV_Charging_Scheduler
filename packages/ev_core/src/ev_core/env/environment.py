"""Environment interface for future request-driven EV charging simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .allocator import AllocationDecision
from .entities import Station, VehicleRequest
from .reward import RewardBreakdown


@dataclass(frozen=True)
class StepResult:
    """Container returned by future environment step calls."""

    observation: dict[str, Any] = field(default_factory=dict)
    reward: RewardBreakdown = field(default_factory=RewardBreakdown)
    done: bool = False
    info: dict[str, Any] = field(default_factory=dict)


class SimulationEnvironment:
    """Placeholder environment with a 15-minute internal step size."""

    def __init__(self, stations: list[Station], resolution_minutes: int = 15) -> None:
        self.stations = stations
        self.resolution_minutes = resolution_minutes

    def reset(self) -> dict[str, Any]:
        """Reset environment state before a new simulation episode."""

        raise NotImplementedError("TODO: implement environment state reset.")

    def step(
        self,
        requests: list[VehicleRequest],
        decisions: list[AllocationDecision],
    ) -> StepResult:
        """Advance the simulation by one 15-minute interval."""

        raise NotImplementedError("TODO: implement environment transition logic.")
