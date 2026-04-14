"""Environment interfaces and Dundee runtime entry point."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .allocator import AllocationDecision
from .entities import Station
from .reward import RewardBreakdown


@dataclass(frozen=True)
class StepResult:
    """Container returned by future environment step calls."""

    observation: dict[str, Any] = field(default_factory=dict)
    reward: RewardBreakdown = field(default_factory=RewardBreakdown)
    done: bool = False
    info: dict[str, Any] = field(default_factory=dict)


class SimulationEnvironment:
    """Base environment with a 15-minute internal step size."""

    def __init__(self, stations: list[Station], resolution_minutes: int = 15) -> None:
        self.stations = stations
        self.resolution_minutes = resolution_minutes

    def reset(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Reset environment state before a new simulation episode."""

        raise NotImplementedError

    def step(self, action: dict[str, str] | list[AllocationDecision] | None = None) -> StepResult:
        """Advance the simulation by one 15-minute interval."""

        raise NotImplementedError


from .dundee_env import DundeeEnv  # noqa: E402

__all__ = ["DundeeEnv", "SimulationEnvironment", "StepResult"]
