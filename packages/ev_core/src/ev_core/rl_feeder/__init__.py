"""Feeder-aligned RL components backed by DigitalTwin public-EV assets."""

from .contracts import FeederAction, FeederEpisodeScenario, FeederRequest

__all__ = [
    "DigitalTwinFeederRLRepository",
    "FeederAction",
    "FeederEpisodeScenario",
    "FeederRequest",
    "FeederStationSelectionEnv",
]


def __getattr__(name: str):
    if name == "DigitalTwinFeederRLRepository":
        from .repository import DigitalTwinFeederRLRepository

        return DigitalTwinFeederRLRepository
    if name == "FeederStationSelectionEnv":
        from .env import FeederStationSelectionEnv

        return FeederStationSelectionEnv
    raise AttributeError(name)
