"""Runtime policy hook for feeder-trained MaskablePPO checkpoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ev_core.contracts.responses import RecommendationOption
from ev_core.grid_advisory.contracts import GridAdvisoryResponse

from .baseline_policies import WeightedScorePolicy
from .ranker import CandidateContext, RecommendationInput
from .scoring_utils import candidate_to_option


class FeederMaskablePPORuntimePolicy:
    """Use a feeder-trained MaskablePPO checkpoint when runtime feeder tensors exist."""

    name = "rl_maskable_ppo_feeder"

    def __init__(
        self,
        *,
        checkpoint_path: str | Path | None = None,
        fallback_policy: WeightedScorePolicy | None = None,
    ) -> None:
        resolved = checkpoint_path or os.getenv("RL_FEEDER_CHECKPOINT_PATH")
        self.checkpoint_path = Path(resolved).expanduser() if resolved else None
        self.fallback_policy = fallback_policy or WeightedScorePolicy()
        self._model: Any | None = None
        self._load_error: str | None = None

    def rank(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        runtime_context = runtime_context or {}
        candidates = self._apply_hard_grid_gate(candidates, runtime_context=runtime_context)
        if not candidates:
            return []

        ranked = self._rank_with_feeder_checkpoint(request, candidates, runtime_context=runtime_context)
        if ranked is not None:
            return ranked
        return self.fallback_policy.rank(request, candidates, runtime_context=runtime_context)

    def _rank_with_feeder_checkpoint(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        *,
        runtime_context: dict[str, Any],
    ) -> list[RecommendationOption] | None:
        model = self._load_model()
        if model is None:
            return None
        observation = runtime_context.get("feeder_observation")
        action_mask = runtime_context.get("feeder_action_mask")
        station_ids = [str(item) for item in runtime_context.get("feeder_station_ids", [])]
        if observation is None or action_mask is None or not station_ids:
            self._load_error = "feeder_runtime_context_missing"
            return None
        action_mask_array = np.asarray(action_mask, dtype=bool)
        if action_mask_array.size != len(station_ids) or not action_mask_array.any():
            return None

        try:
            action, _state = model.predict(
                np.asarray(observation, dtype=np.float32),
                deterministic=True,
                action_masks=action_mask_array,
            )
        except Exception as exc:
            self._load_error = f"prediction_failed: {exc}"
            return None

        action_index = int(np.asarray(action).reshape(-1)[0])
        if action_index < 0 or action_index >= len(station_ids) or not action_mask_array[action_index]:
            return None
        selected_station_id = station_ids[action_index]
        candidate_by_station = {str(candidate.station_id): candidate for candidate in candidates}
        selected_candidate = candidate_by_station.get(selected_station_id)
        if selected_candidate is None:
            return None

        fallback_options = self.fallback_policy.rank(request, candidates, runtime_context=runtime_context)
        selected = candidate_to_option(
            selected_candidate,
            score=1.0,
            reason_tags=["rl_maskable_ppo_feeder", "checkpoint_selected"],
        )
        selected = selected.model_copy(
            update={
                "metadata": {
                    **selected.metadata,
                    "rl_policy_checkpoint_path": None if self.checkpoint_path is None else str(self.checkpoint_path),
                    "rl_policy_scope": "digitaltwin_feeder_public_ev",
                }
            }
        )
        return [selected, *[option for option in fallback_options if option.station_id != selected.station_id]]

    def _apply_hard_grid_gate(
        self,
        candidates: Sequence[CandidateContext],
        *,
        runtime_context: dict[str, Any],
    ) -> list[CandidateContext]:
        advisories = runtime_context.get("grid_advisories")
        if not isinstance(advisories, dict):
            return list(candidates)
        filtered: list[CandidateContext] = []
        for candidate in candidates:
            advisory = advisories.get(str(candidate.station_id))
            if _is_hard_grid_reject(advisory):
                continue
            filtered.append(candidate)
        return filtered

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


def _is_hard_grid_reject(advisory: object) -> bool:
    if advisory is None:
        return False
    if isinstance(advisory, dict):
        verdict = str(advisory.get("verdict") or "").upper()
        risk_class = str(advisory.get("risk_class") or "").upper()
        opf_feasible = bool(advisory.get("opf_feasible", True))
    elif isinstance(advisory, GridAdvisoryResponse):
        verdict = str(advisory.verdict).upper()
        risk_class = str(advisory.risk_class).upper()
        opf_feasible = bool(advisory.opf_feasible)
    else:
        return False
    return verdict == "REJECT" or risk_class == "VIOLATION" or not opf_feasible


__all__ = ["FeederMaskablePPORuntimePolicy"]
