"""Checkpoint-backed MaskablePPO recommendation policy with safe fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ev_core.config.deployment import rl_deployment_config_from_env
from ev_core.contracts.responses import RecommendationOption
from ev_core.grid_advisory.client import GridAdvisoryClient, grid_advisory_client_from_env
from ev_core.grid_advisory.contracts import GridAdvisoryResponse
from ev_core.grid_advisory.feature_mapping import build_grid_schedule_proposal

from .baseline_policies import WeightedScorePolicy
from .ranker import CandidateContext, RecommendationInput
from .scoring_utils import candidate_to_option


class MaskablePPORuntimePolicy:
    """Use a trained MaskablePPO checkpoint to rank stations when available."""

    name = "rl_maskable_ppo"

    def __init__(
        self,
        *,
        checkpoint_path: str | Path | None = None,
        fallback_policy: WeightedScorePolicy | None = None,
        grid_advisory_client: GridAdvisoryClient | None = None,
    ) -> None:
        deployment_config = rl_deployment_config_from_env()
        resolved_checkpoint = checkpoint_path if checkpoint_path is not None else deployment_config.checkpoint_path
        self.checkpoint_path = Path(resolved_checkpoint).expanduser() if resolved_checkpoint else None
        self.fail_closed = bool(deployment_config.fail_closed)
        self.fallback_policy = fallback_policy or WeightedScorePolicy()
        self.grid_advisory_client = grid_advisory_client or grid_advisory_client_from_env()
        self._model: Any | None = None
        self._load_error: str | None = None

    def rank(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        if not candidates:
            return []

        ranked = self._rank_with_checkpoint(request, candidates, runtime_context=runtime_context or {})
        if ranked is not None:
            return ranked
        if self.fail_closed:
            return []
        return self.fallback_policy.rank(request, candidates, runtime_context=runtime_context)

    def _rank_with_checkpoint(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        *,
        runtime_context: dict[str, Any],
    ) -> list[RecommendationOption] | None:
        model = self._load_model()
        if model is None:
            return None

        simulation_request = runtime_context.get("simulation_request")
        if simulation_request is None or not hasattr(simulation_request, "latest_finish_ts"):
            return None

        station_ids = [str(item) for item in runtime_context.get("station_ids", [])]
        if not station_ids:
            station_ids = sorted(str(candidate.station_id) for candidate in candidates)
        candidate_by_station = {str(candidate.station_id): candidate for candidate in candidates}
        action_mask = [station_id in candidate_by_station for station_id in station_ids]
        if not any(action_mask):
            return None

        grid_advisories = self._grid_advisories(
            simulation_request=simulation_request,
            candidates=candidates,
            runtime_context=runtime_context,
        )
        from ev_core.rl.observations import ObservationBuilder

        observation = ObservationBuilder(station_ids=station_ids).build(
            request=simulation_request,
            current_time=runtime_context.get("simulated_timestamp") or getattr(simulation_request, "arrival_ts", None),
            station_features=candidate_by_station,
            action_mask=action_mask,
            station_grid_features=grid_advisories,
        )
        try:
            action, _state = model.predict(
                observation,
                deterministic=True,
                action_masks=np.asarray(action_mask, dtype=bool),
            )
        except Exception as exc:
            self._load_error = f"prediction_failed: {exc}"
            return None

        action_index = int(np.asarray(action).reshape(-1)[0])
        if action_index < 0 or action_index >= len(station_ids) or not action_mask[action_index]:
            return None

        selected_station_id = station_ids[action_index]
        selected_candidate = candidate_by_station.get(selected_station_id)
        if selected_candidate is None:
            return None

        fallback_options = self.fallback_policy.rank(request, candidates, runtime_context=runtime_context)
        fallback_by_station = {option.station_id: option for option in fallback_options}
        selected = candidate_to_option(
            selected_candidate,
            score=1.0,
            reason_tags=["rl_maskable_ppo", "checkpoint_selected"],
        )
        alternatives = [option for option in fallback_options if option.station_id != selected.station_id]
        if selected.station_id in fallback_by_station:
            selected = selected.model_copy(
                update={
                    "metadata": {
                        **fallback_by_station[selected.station_id].metadata,
                        **selected.metadata,
                        "rl_policy_checkpoint_path": str(self.checkpoint_path),
                    }
                }
            )
        return [selected, *alternatives]

    def _load_model(self) -> Any | None:
        if self._model is not None:
            return self._model
        if self.checkpoint_path is None or not self.checkpoint_path.exists():
            self._load_error = "checkpoint_missing"
            return None
        try:
            from sb3_contrib import MaskablePPO
        except ImportError as exc:
            self._load_error = f"sb3_contrib_missing: {exc}"
            return None
        try:
            self._model = MaskablePPO.load(str(self.checkpoint_path))
        except Exception as exc:
            self._load_error = f"checkpoint_load_failed: {exc}"
            return None
        return self._model

    def _grid_advisories(
        self,
        *,
        simulation_request: Any,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any],
    ) -> dict[str, GridAdvisoryResponse]:
        provided = runtime_context.get("grid_advisories")
        if isinstance(provided, dict):
            return provided
        proposals = [
            build_grid_schedule_proposal(
                request=simulation_request,
                candidate=candidate,
                episode_id=str(runtime_context.get("episode_id") or ""),
            )
            for candidate in candidates
        ]
        responses = self.grid_advisory_client.batch_evaluate(proposals)
        return {
            str(candidate.station_id): response
            for candidate, response in zip(candidates, responses)
        }


__all__ = ["MaskablePPORuntimePolicy"]
