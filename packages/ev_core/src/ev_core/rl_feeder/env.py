"""Gymnasium environment for feeder-aligned public-EV station selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError as exc:  # pragma: no cover - exercised by import behavior
    gym = None
    spaces = None
    _GYM_IMPORT_ERROR = exc
else:
    _GYM_IMPORT_ERROR = None

from ev_core.grid_advisory.client import GridAdvisoryClient, build_grid_advisory_client
from ev_core.grid_advisory.contracts import GridAdvisoryResponse, GridSchedulePoint, GridScheduleProposal

from .contracts import FeederAction, FeederEpisodeScenario, FeederRequest
from .observations import FeederObservationBuilder
from .repository import DigitalTwinFeederRLRepository
from .requests import FeederRequestGenerator
from .rewards import FeederRewardBreakdown, FeederStationSelectionReward
from .scenarios import FeederScenarioSampler


class FeederStationSelectionEnv((gym.Env if gym is not None else object)):
    """Single-agent masked RL environment over DigitalTwin public-EV feeder nodes."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        feeder_rl_data_dir: str | Path,
        scenario: FeederEpisodeScenario | None = None,
        repository: DigitalTwinFeederRLRepository | None = None,
        request_generator: FeederRequestGenerator | None = None,
        grid_advisory_mode: str = "disabled",
        grid_evaluation_mode: str = "replay",
        grid_advisory_client: GridAdvisoryClient | None = None,
        grid_advisory_replay_dir: str | Path | None = None,
        grid_advisory_base_url: str | None = None,
        grid_advisory_timeout_seconds: float = 2.0,
        min_truth_level: str = "any",
        exclude_adapter_proxy: bool = False,
    ) -> None:
        if gym is None or spaces is None:
            raise ImportError("Gymnasium is required to use FeederStationSelectionEnv.") from _GYM_IMPORT_ERROR

        self.feeder_rl_data_dir = Path(feeder_rl_data_dir).resolve()
        self.repository = repository or DigitalTwinFeederRLRepository(self.feeder_rl_data_dir)
        self.actions: list[FeederAction] = self.repository.load_actions()
        if not self.actions:
            raise ValueError(f"No feeder public-EV actions found in {self.feeder_rl_data_dir}.")

        self.request_generator = request_generator or FeederRequestGenerator(
            priors=self.repository.load_request_priors(),
            actions=self.actions,
            seed="feeder-rl-env",
        )
        self.scenario_sampler = FeederScenarioSampler(actions=self.actions)
        self.scenario = scenario or self.scenario_sampler.sample(seed=0, grid_evaluation_mode=grid_evaluation_mode)
        self.grid_advisory_mode = str(grid_advisory_mode or "disabled").strip().lower()
        self.grid_evaluation_mode = str(grid_evaluation_mode or self.scenario.grid_evaluation_mode or "replay").strip().lower()
        self.grid_advisory_client = grid_advisory_client or build_grid_advisory_client(
            mode=self.grid_advisory_mode,
            replay_dir=grid_advisory_replay_dir or self.feeder_rl_data_dir,
            base_url=grid_advisory_base_url,
            timeout_seconds=grid_advisory_timeout_seconds,
            min_truth_level=min_truth_level,
            exclude_adapter_proxy=exclude_adapter_proxy,
        )

        self.observation_builder = FeederObservationBuilder(
            actions=self.actions,
            feature_stats=self.repository.load_feature_stats(),
        )
        self.reward_model = FeederStationSelectionReward()
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.observation_builder.spec.vector_size,),
            dtype=np.float32,
        )

        self.requests: list[FeederRequest] = []
        self.request_index = 0
        self.current_request: FeederRequest | None = None
        self.current_action_mask: list[bool] = [False] * len(self.actions)
        self.current_grid_advisories: dict[str, GridAdvisoryResponse] = {}
        self.last_reward_breakdown = FeederRewardBreakdown()
        self.last_selected_grid_advisory: GridAdvisoryResponse | None = None
        self.terminated = False

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        if options and options.get("scenario") is not None:
            self.scenario = options["scenario"]
        elif seed is not None:
            self.scenario = self.scenario_sampler.sample(
                seed=int(seed),
                grid_evaluation_mode=self.grid_evaluation_mode,
            )
        self.requests = self.request_generator.generate_for_scenario(self.scenario)
        self.request_index = 0
        self.terminated = False
        self._prepare_current_request()
        return self._build_observation(), self._build_info()

    def step(self, action: int):
        if self.terminated:
            raise RuntimeError("Episode already terminated. Call reset() before step().")

        selected_action: FeederAction | None = None
        selected_grid_advisory: GridAdvisoryResponse | None = None
        invalid_action = False
        missed = False

        if self.current_request is None:
            self.terminated = True
            return self.observation_builder.zeros(), 0.0, True, False, self._build_info()

        if not any(self.current_action_mask):
            reward_breakdown = self.reward_model.compute(missed=True)
            missed = True
        elif action < 0 or action >= len(self.actions) or not self.current_action_mask[action]:
            reward_breakdown = self.reward_model.compute(invalid_action=True)
            invalid_action = True
        else:
            selected_action = self.actions[action]
            selected_grid_advisory = self.current_grid_advisories.get(selected_action.station_id)
            reward_breakdown = self.reward_model.compute(
                selected_action=selected_action,
                request=self.current_request,
                grid_advisory=selected_grid_advisory,
            )

        self.last_reward_breakdown = reward_breakdown
        self.last_selected_grid_advisory = selected_grid_advisory
        self.request_index += 1
        self._prepare_current_request()
        terminated = self.current_request is None
        self.terminated = terminated
        info = self._build_info(
            selected_action=selected_action,
            invalid_action=invalid_action,
            missed=missed,
        )
        return self._build_observation(), float(reward_breakdown.total), terminated, False, info

    def action_masks(self) -> list[bool]:
        return [bool(value) for value in self.current_action_mask]

    def valid_action_mask(self) -> list[bool]:
        return self.action_masks()

    def _prepare_current_request(self) -> None:
        if self.request_index >= len(self.requests):
            self.current_request = None
            self.current_action_mask = [False] * len(self.actions)
            self.current_grid_advisories = {}
            return
        self.current_request = self.requests[self.request_index]
        self.current_action_mask = [
            self._is_action_valid_for_request(action, self.current_request)
            for action in self.actions
        ]
        self.current_grid_advisories = self._build_grid_advisories(self.current_request)

    def _build_observation(self) -> np.ndarray:
        return self.observation_builder.build(
            request=self.current_request,
            action_mask=self.current_action_mask,
            grid_advisories=self.current_grid_advisories,
        )

    def _build_grid_advisories(self, request: FeederRequest) -> dict[str, GridAdvisoryResponse]:
        valid_actions = [
            action for action, valid in zip(self.actions, self.current_action_mask) if valid
        ]
        if not valid_actions:
            return {}
        proposals = [self._proposal_for_action(request, action) for action in valid_actions]
        responses = self.grid_advisory_client.batch_evaluate(proposals)
        return {
            action.station_id: response
            for action, response in zip(valid_actions, responses)
        }

    def _proposal_for_action(self, request: FeederRequest, action: FeederAction) -> GridScheduleProposal:
        charger_limit_kw = request.max_dc_kw if _prefers_dc(request) else request.max_ac_kw
        charger_kw = max(min(action.charger_kw, action.public_ev_capacity_kw, charger_limit_kw), 0.0)
        duration_hours = max(request.requested_energy_kwh / max(charger_kw, 1.0), 0.5)
        duration_steps = max(int(np.ceil(duration_hours * 60.0 / 30.0)), 1)
        ev_schedule = [
            GridSchedulePoint(time_index=step, p_kw=charger_kw, q_kvar=0.0)
            for step in range(duration_steps)
        ]
        return GridScheduleProposal(
            request_id=request.request_id,
            episode_id=self.scenario.scenario_id,
            station_id=action.station_id,
            area_id=action.secondary_area_id,
            secondary_area_id=action.secondary_area_id,
            demand_point_id=action.demand_point_id,
            node_id=action.node_id,
            asset_type="public_ev",
            source_system=action.source_system,
            start_timestamp=request.arrival_timestamp,
            timebase_minutes=30,
            duration_steps=duration_steps,
            requested_energy_kwh=request.requested_energy_kwh,
            charger_kw=charger_kw,
            ev_schedule=ev_schedule,
            evaluation_mode=self.grid_evaluation_mode,
        )

    def _is_action_valid_for_request(self, action: FeederAction, request: FeederRequest) -> bool:
        if action.secondary_area_id != request.secondary_area_id:
            return False
        if action.charger_kw <= 0.0 or action.public_ev_capacity_kw <= 0.0:
            return False
        if _prefers_dc(request):
            return action.connector_type in {"dc", "rapid", "ultra_rapid", "any"} or action.charger_kw >= 43.0
        return action.connector_type in {"ac", "dc", "rapid", "ultra_rapid", "any"}

    def _build_info(
        self,
        *,
        selected_action: FeederAction | None = None,
        invalid_action: bool = False,
        missed: bool = False,
    ) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "split": self.scenario.split,
            "secondary_area_id": self.scenario.secondary_area_id,
            "request_index": self.request_index,
            "request_id": None if self.current_request is None else self.current_request.request_id,
            "valid_action_count": int(sum(self.current_action_mask)),
            "selected_station_id": None if selected_action is None else selected_action.station_id,
            "selected_node_id": None if selected_action is None else selected_action.node_id,
            "invalid_action": invalid_action,
            "missed": missed,
            "decision_mode": "feeder_public_ev_station_selection",
            "reward_breakdown": self.last_reward_breakdown.to_dict(),
            "grid_advisory_mode": self.grid_advisory_mode,
            "grid_evaluation_mode": self.grid_evaluation_mode,
            "selected_grid_advisory": (
                None
                if self.last_selected_grid_advisory is None
                else self.last_selected_grid_advisory.model_dump(mode="json")
            ),
        }


def _prefers_dc(request: FeederRequest) -> bool:
    return str(request.charger_type_preference).strip().lower() in {"dc", "rapid", "ultra_rapid"}


__all__ = ["FeederStationSelectionEnv"]
