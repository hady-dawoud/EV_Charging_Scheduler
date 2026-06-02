"""Training-facing wrapper around the existing Dundee RL environment."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ev_core.rl.contracts import RLEpisodeScenario

from .data_adapter import DEFAULT_REQUEST_GENERATOR_SEED, DundeeTrainingDataAdapter
from .scenario_factory import OfflineDundeeScenarioFactory, OfflineTrainingScenarioRequest

if TYPE_CHECKING:
    import numpy as np
    from ev_core.rl.env import DundeeStationSelectionEnv


def _build_core_env(
    *,
    repo_root: Path,
    scenario: RLEpisodeScenario,
    data_adapter: DundeeTrainingDataAdapter,
):
    from ev_core.rl.env import DundeeStationSelectionEnv

    return DundeeStationSelectionEnv(
        repo_root=repo_root,
        scenario=scenario,
        bundle=data_adapter.load_bundle(),
        request_generator=data_adapter.build_request_generator(seed=DEFAULT_REQUEST_GENERATOR_SEED),
    )


class OfflineDundeeStationSelectionEnv:
    """Headless offline-training boundary that delegates to the existing RL env."""

    def __init__(
        self,
        *,
        repo_root: str | Path,
        scenario: RLEpisodeScenario,
        data_adapter: DundeeTrainingDataAdapter | None = None,
        core_env: "DundeeStationSelectionEnv | None" = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.data_adapter = data_adapter or DundeeTrainingDataAdapter(self.repo_root)
        self.scenario = scenario
        self.core_env = core_env or _build_core_env(
            repo_root=self.repo_root,
            scenario=scenario,
            data_adapter=self.data_adapter,
        )

    @classmethod
    def from_request(
        cls,
        *,
        repo_root: str | Path,
        request: OfflineTrainingScenarioRequest,
        data_adapter: DundeeTrainingDataAdapter | None = None,
    ) -> "OfflineDundeeStationSelectionEnv":
        resolved_root = Path(repo_root).resolve()
        adapter = data_adapter or DundeeTrainingDataAdapter(resolved_root)
        scenario_bundle = OfflineDundeeScenarioFactory(
            repo_root=resolved_root,
            data_adapter=adapter,
        ).build(request)
        return cls(
            repo_root=resolved_root,
            scenario=scenario_bundle.scenario,
            data_adapter=adapter,
        )

    @property
    def action_space(self):
        return self.core_env.action_space

    @property
    def observation_space(self):
        return self.core_env.observation_space

    @property
    def station_ids(self) -> list[str]:
        return list(self.core_env.station_ids)

    @property
    def current_request(self):
        return self.core_env.current_request

    @property
    def current_candidate_contexts(self):
        return list(self.core_env.current_candidate_contexts)

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        return self.core_env.reset(seed=seed, options=options)

    def step(self, action: int):
        return self.core_env.step(action)

    def action_masks(self) -> list[bool]:
        return list(self.core_env.action_masks())

    def valid_action_mask(self) -> list[bool]:
        return self.action_masks()


__all__ = ["OfflineDundeeStationSelectionEnv"]
