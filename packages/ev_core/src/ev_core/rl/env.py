"""Gymnasium-compatible single-agent masked station-selection environment skeleton."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError as exc:  # pragma: no cover - exercised via import behavior
    gym = None
    spaces = None
    _GYM_IMPORT_ERROR = exc
else:
    _GYM_IMPORT_ERROR = None

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.env.dundee_env import DundeeEnv
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.routing.osmnx_provider import OSMnxRoutingProvider
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider
from ev_core.topology.scenarios import TopologyScenario
from ev_core.utils.timebase import floor_to_timebase
from ev_core.vehicles.profiles import get_default_vehicle_profiles

from .action_mask import build_station_action_mask
from .contracts import RLEpisodeScenario
from .observations import ObservationBuilder
from .rewards import RewardBreakdown, StationSelectionReward
from .scenarios import generate_requests_for_scenario


class DundeeStationSelectionEnv((gym.Env if gym is not None else object)):
    """Decision-level single-agent env for masked station selection.

    PR3 keeps this environment intentionally simple and decision-centric: each step
    evaluates one external-live request against Dundee candidate contexts, returns a
    masked discrete station choice, computes reward from the chosen feasible option,
    and advances to the next request. Full closed-loop queue/session mutation can be
    layered in later without changing the core action/observation/reward contracts.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        repo_root: str | Path,
        scenario: RLEpisodeScenario,
        bundle: Any | None = None,
        request_generator: SyntheticLiveRequestGenerator | None = None,
    ) -> None:
        if gym is None or spaces is None:
            raise ImportError("Gymnasium is required to use DundeeStationSelectionEnv.") from _GYM_IMPORT_ERROR
        self.repo_root = Path(repo_root).resolve()
        self.repository = DundeeSimulationRepository(self.repo_root)
        self.bundle = bundle or self.repository.load_bundle()
        self.scenario = scenario
        self.request_generator = request_generator or SyntheticLiveRequestGenerator(
            request_generator_params=self.bundle.request_generator_params,
            stations=self.bundle.stations.to_dict(orient="records"),
            vehicle_profiles=get_default_vehicle_profiles(),
            seed="rl-env",
        )
        self.station_ids = sorted(self.bundle.stations["station_id"].astype(str).tolist())
        self.observation_builder = ObservationBuilder(station_ids=self.station_ids)
        self.reward_model = StationSelectionReward()
        self.action_space = spaces.Discrete(len(self.station_ids))
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.observation_builder.spec.vector_size,),
            dtype=np.float32,
        )
        self.runtime_env: DundeeEnv | None = None
        self.requests: list[Any] = []
        self.request_index = 0
        self.current_request = None
        self.current_simulation_request = None
        self.current_candidate_contexts: list[Any] = []
        self.current_action_mask: list[bool] = [False] * len(self.station_ids)
        self.last_reward_breakdown = RewardBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.terminated = False

    @property
    def _current_request(self):
        return self.current_request

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        if options and options.get("scenario") is not None:
            self.scenario = options["scenario"]
        elif seed is not None:
            self.scenario = replace(self.scenario, seed=int(seed))
        self.runtime_env = self._build_runtime_env(self.scenario)
        self.runtime_env.start()
        self.requests = generate_requests_for_scenario(
            self.scenario,
            request_generator=self.request_generator,
        )
        self.request_index = 0
        self.terminated = False
        self._prepare_current_request()
        observation = self._build_observation()
        return observation, self._build_info()

    def step(self, action: int):
        if self.terminated:
            raise RuntimeError("Episode already terminated. Call reset() before step().")

        if self.current_request is None:
            self.terminated = True
            return self.observation_builder.zeros(), 0.0, True, False, self._build_info()

        selected_station_id = None
        invalid_action = False
        missed = False

        if not any(self.current_action_mask):
            reward_breakdown = self.reward_model.compute(missed=True)
            missed = True
        elif action < 0 or action >= len(self.station_ids) or not self.current_action_mask[action]:
            reward_breakdown = self.reward_model.compute(invalid_action=True)
            invalid_action = True
        else:
            selected_station_id = self.station_ids[action]
            chosen_context = next(
                candidate for candidate in self.current_candidate_contexts if str(candidate.station_id) == selected_station_id
            )
            reward_breakdown = self.reward_model.compute(selected_option=chosen_context)

        self.last_reward_breakdown = reward_breakdown
        self.request_index += 1
        self._prepare_current_request()
        terminated = self.current_request is None
        self.terminated = terminated
        observation = self._build_observation()
        info = self._build_info(
            selected_station_id=selected_station_id,
            invalid_action=invalid_action,
            missed=missed,
        )
        return observation, float(reward_breakdown.total), terminated, False, info

    def action_masks(self):
        return list(bool(value) for value in self.current_action_mask)

    def valid_action_mask(self):
        return self.action_masks()

    def _prepare_current_request(self) -> None:
        if self.request_index >= len(self.requests):
            self.current_request = None
            self.current_simulation_request = None
            self.current_candidate_contexts = []
            self.current_action_mask = [False] * len(self.station_ids)
            return
        request = self.requests[self.request_index]
        assert self.runtime_env is not None
        self.runtime_env.current_time = floor_to_timebase(request.request_timestamp)
        simulation_request = self.runtime_env._build_simulation_request_from_external(request)
        candidates = self.runtime_env._build_candidate_contexts(simulation_request)
        station_rows = [self.runtime_env.station_index[station_id] for station_id in self.station_ids]
        action_mask = build_station_action_mask(
            request=simulation_request,
            stations=station_rows,
            candidate_contexts=candidates,
        )
        self.current_request = request
        self.current_simulation_request = simulation_request
        self.current_candidate_contexts = candidates
        self.current_action_mask = action_mask

    def _build_observation(self) -> np.ndarray:
        if self.current_request is None or self.runtime_env is None:
            return self.observation_builder.zeros()
        station_features = {str(candidate.station_id): candidate for candidate in self.current_candidate_contexts}
        return self.observation_builder.build(
            request=self.current_request,
            current_time=self.runtime_env.current_time,
            station_features=station_features,
            action_mask=self.current_action_mask,
        )

    def _build_info(
        self,
        *,
        selected_station_id: str | None = None,
        invalid_action: bool = False,
        missed: bool = False,
    ) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "split": self.scenario.split,
            "demand_level": self.scenario.demand_level,
            "request_index": self.request_index,
            "request_id": None if self.current_request is None else self.current_request.request_id,
            "valid_action_count": int(sum(self.current_action_mask)),
            "selected_station_id": selected_station_id,
            "invalid_action": invalid_action,
            "missed": missed,
            "decision_mode": "decision_only_skeleton",
            "reward_breakdown": self.last_reward_breakdown.to_dict(),
            "routing_provider_name": self.scenario.routing_provider_name,
            "dynamic_pricing_enabled": self.scenario.dynamic_pricing_enabled,
        }

    def _build_runtime_env(self, scenario: RLEpisodeScenario) -> DundeeEnv:
        topology_scenario: TopologyScenario | None = None
        if scenario.topology_scenario_id:
            topology_scenario = self.repository.load_topology_scenario(scenario.topology_scenario_id)
        return DundeeEnv(
            self.bundle,
            policy_mode="overload_aware",
            replay_year=scenario.start_ts.year,
            start_time=scenario.start_ts,
            runtime_mode="scenario",
            demand_multiplier=scenario.demand_multiplier,
            operational_start_time=scenario.start_ts,
            warm_start_minutes=0,
            replay_window_start=scenario.start_ts,
            replay_window_end=scenario.end_ts,
            topology_scenario=topology_scenario,
            dynamic_pricing_enabled=scenario.dynamic_pricing_enabled,
            routing_provider=self._build_routing_provider(scenario),
        )

    def _build_routing_provider(self, scenario: RLEpisodeScenario):
        name = str(scenario.routing_provider_name or "simple_distance").strip().lower()
        if name == "osmnx":
            return OSMnxRoutingProvider(graph_path=self.repo_root / "data" / "processed" / "routing" / "dundee_drive.graphml")
        return SimpleDistanceRoutingProvider()


__all__ = ["DundeeStationSelectionEnv"]
