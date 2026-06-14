"""Runtime policy hook for feeder-trained MaskablePPO checkpoints."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ev_core.config.deployment import rl_deployment_config_from_env
from ev_core.contracts.responses import RecommendationOption
from ev_core.grid_advisory.contracts import GridAdvisoryResponse

from .baseline_policies import WeightedScorePolicy
from .ranker import CandidateContext, RecommendationInput
from .scoring_utils import candidate_to_option


DEFAULT_FEEDER_CHECKPOINT_PATH = Path("models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip")


@dataclass(frozen=True)
class FeederActionPrediction:
    available: bool
    action_index: int | None
    station_id: str | None
    fallback_used: bool
    error: str | None


class FeederMaskablePPORuntimePolicy:
    """Use a feeder-trained MaskablePPO checkpoint when runtime feeder tensors exist."""

    name = "rl_maskable_ppo_feeder"

    def __init__(
        self,
        *,
        checkpoint_path: str | Path | None = None,
        fallback_policy: WeightedScorePolicy | None = None,
    ) -> None:
        deployment_config = rl_deployment_config_from_env()
        resolved = checkpoint_path or os.getenv("RL_FEEDER_CHECKPOINT_PATH")
        self.checkpoint_path = Path(resolved).expanduser() if resolved else DEFAULT_FEEDER_CHECKPOINT_PATH
        self.fail_closed = bool(deployment_config.fail_closed)
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
        if self.fail_closed:
            return []
        fallback_options = self.fallback_policy.rank(request, candidates, runtime_context=runtime_context)
        return self._with_policy_metadata(
            fallback_options,
            runtime_context=runtime_context,
            fallback_used=True,
            fallback_reason=self._load_error or "feeder_policy_unavailable",
            extra={"fallback_policy_name": self.fallback_policy.name},
        )

    def predict_feeder_action(
        self,
        runtime_context: dict[str, Any],
    ) -> FeederActionPrediction:
        model = self._load_model()
        if model is None:
            return FeederActionPrediction(
                available=False,
                action_index=None,
                station_id=None,
                fallback_used=True,
                error=self._load_error or "feeder_policy_unavailable",
            )
        validated = self._validated_runtime_inputs(model, runtime_context)
        if validated is None:
            return FeederActionPrediction(
                available=False,
                action_index=None,
                station_id=None,
                fallback_used=True,
                error=self._load_error or "feeder_runtime_context_invalid",
            )
        observation, action_mask, station_ids = validated
        try:
            action, _state = model.predict(
                observation,
                deterministic=True,
                action_masks=action_mask,
            )
        except Exception as exc:
            self._load_error = f"prediction_failed: {exc}"
            return FeederActionPrediction(
                available=False,
                action_index=None,
                station_id=None,
                fallback_used=True,
                error=self._load_error,
            )
        try:
            action_index = int(np.asarray(action).reshape(-1)[0])
        except Exception as exc:
            self._load_error = f"predicted_action_invalid: {exc}"
            return FeederActionPrediction(
                available=False,
                action_index=None,
                station_id=None,
                fallback_used=True,
                error=self._load_error,
            )
        if action_index < 0 or action_index >= len(station_ids):
            self._load_error = "predicted_action_out_of_range"
            return FeederActionPrediction(
                available=False,
                action_index=None,
                station_id=None,
                fallback_used=True,
                error=self._load_error,
            )
        if not action_mask[action_index]:
            self._load_error = "predicted_action_masked_out"
            return FeederActionPrediction(
                available=False,
                action_index=None,
                station_id=None,
                fallback_used=True,
                error=self._load_error,
            )
        return FeederActionPrediction(
            available=True,
            action_index=action_index,
            station_id=station_ids[action_index],
            fallback_used=False,
            error=None,
        )

    def _rank_with_feeder_checkpoint(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        *,
        runtime_context: dict[str, Any],
    ) -> list[RecommendationOption] | None:
        prediction = self.predict_feeder_action(runtime_context)
        if not prediction.available:
            return None
        action_index = int(prediction.action_index)
        selected_station_id = str(prediction.station_id)
        action_mask_array = np.asarray(
            runtime_context["feeder_action_mask"],
            dtype=bool,
        ).reshape(-1)
        candidate_by_station = {str(candidate.station_id): candidate for candidate in candidates}
        selected_candidate = candidate_by_station.get(selected_station_id)
        fallback_options = self.fallback_policy.rank(request, candidates, runtime_context=runtime_context)
        if not fallback_options:
            self._load_error = "no_app_candidates_available"
            return None

        if selected_candidate is None:
            selected, mapping_metadata = self._mapped_app_option_for_feeder_action(
                fallback_options,
                action_index=action_index,
                action_mask=action_mask_array,
            )
        else:
            selected = candidate_to_option(
                selected_candidate,
                score=1.0,
                reason_tags=["rl_maskable_ppo_feeder", "checkpoint_selected"],
            )
            mapping_metadata = {
                "feeder_station_candidate_match": True,
                "feeder_candidate_mapping_strategy": "candidate_station_id_match",
            }

        selected = self._with_policy_metadata(
            [selected],
            runtime_context=runtime_context,
            fallback_used=False,
            fallback_reason=None,
            extra={
                **mapping_metadata,
                "feeder_selected_action_index": action_index,
                "feeder_selected_station_id": selected_station_id,
            },
        )[0]
        return [selected, *[option for option in fallback_options if option.station_id != selected.station_id]]

    def _validated_runtime_inputs(
        self,
        model: Any,
        runtime_context: dict[str, Any],
    ) -> tuple[np.ndarray, np.ndarray, list[str]] | None:
        observation = runtime_context.get("feeder_observation")
        action_mask = runtime_context.get("feeder_action_mask")
        if observation is None:
            self._load_error = "feeder_observation_missing"
            return None
        if action_mask is None:
            self._load_error = "feeder_action_mask_missing"
            return None
        raw_station_ids = runtime_context.get("feeder_station_ids")
        if raw_station_ids is None:
            self._load_error = "feeder_station_ids_missing"
            return None
        try:
            station_ids = [str(item) for item in raw_station_ids]
        except Exception as exc:
            self._load_error = f"feeder_station_ids_invalid: {exc}"
            return None
        if not station_ids:
            self._load_error = "feeder_station_ids_missing"
            return None
        try:
            observation_array = np.asarray(observation, dtype=np.float32)
        except Exception as exc:
            self._load_error = f"feeder_observation_invalid: {exc}"
            return None
        expected_size = _model_observation_size(model)
        if expected_size is not None and int(observation_array.size) != expected_size:
            self._load_error = "feeder_observation_shape_mismatch"
            return None
        try:
            action_mask_array = np.asarray(action_mask, dtype=bool).reshape(-1)
        except Exception as exc:
            self._load_error = f"feeder_action_mask_invalid: {exc}"
            return None
        if action_mask_array.size != len(station_ids):
            self._load_error = "feeder_mask_station_length_mismatch"
            return None
        if not action_mask_array.any():
            self._load_error = "feeder_no_valid_actions"
            return None
        return observation_array, action_mask_array, station_ids

    def _mapped_app_option_for_feeder_action(
        self,
        fallback_options: Sequence[RecommendationOption],
        *,
        action_index: int,
        action_mask: np.ndarray,
    ) -> tuple[RecommendationOption, dict[str, Any]]:
        valid_indices = [idx for idx, is_valid in enumerate(action_mask) if bool(is_valid)]
        valid_ordinal = valid_indices.index(action_index) if action_index in valid_indices else action_index
        mapped_index = valid_ordinal % len(fallback_options)
        selected = fallback_options[mapped_index].model_copy(
            update={
                "score": 1.0,
                "reason_tags": ["rl_maskable_ppo_feeder", "offline_demo_mapping"],
            }
        )
        return selected, {
            "feeder_station_candidate_match": False,
            "feeder_candidate_mapping_strategy": "offline_demo_valid_action_ordinal_bridge",
            "feeder_valid_action_ordinal": valid_ordinal,
        }

    def _with_policy_metadata(
        self,
        options: Sequence[RecommendationOption],
        *,
        runtime_context: dict[str, Any],
        fallback_used: bool,
        fallback_reason: str | None,
        extra: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        metadata = self._policy_metadata(
            runtime_context,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            extra=extra or {},
        )
        return [
            option.model_copy(update={"metadata": {**option.metadata, **metadata}})
            for option in options
        ]

    def _policy_metadata(
        self,
        runtime_context: dict[str, Any],
        *,
        fallback_used: bool,
        fallback_reason: str | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        action_mask = runtime_context.get("feeder_action_mask")
        station_ids = runtime_context.get("feeder_station_ids") or []
        observation = runtime_context.get("feeder_observation")
        observation_shape = runtime_context.get("feeder_observation_shape")
        if observation_shape is None and observation is not None:
            observation_shape = list(np.asarray(observation).shape)
        action_mask_array = np.asarray(action_mask, dtype=bool).reshape(-1) if action_mask is not None else None
        feeder_action_count = runtime_context.get("feeder_action_count") or len(station_ids)
        feeder_valid_action_count = runtime_context.get("feeder_valid_action_count")
        if feeder_valid_action_count is None and action_mask_array is not None:
            feeder_valid_action_count = int(action_mask_array.sum())
        checkpoint_path = None if self.checkpoint_path is None else str(self.checkpoint_path)
        metadata = {
            "effective_policy_name": self.name,
            "policy_name": self.name,
            "policy_source": runtime_context.get("policy_source", "policy_runtime"),
            "rl_policy_name": self.name,
            "rl_policy_scope": "digitaltwin_feeder_public_ev",
            "rl_policy_attempted": True,
            "rl_policy_checkpoint_path": checkpoint_path,
            "checkpoint_path": checkpoint_path,
            "fallback_used": bool(fallback_used),
            "fallback_reason": fallback_reason,
            "rl_policy_fallback_used": bool(fallback_used),
            "rl_policy_fallback_reason": fallback_reason,
            "feeder_context_available": bool(runtime_context.get("feeder_observation") is not None),
            "feeder_data_dir": runtime_context.get("feeder_data_dir"),
            "feeder_observation_shape": observation_shape,
            "feeder_action_count": feeder_action_count,
            "feeder_valid_action_count": feeder_valid_action_count,
            "feeder_selected_secondary_area_id": runtime_context.get("feeder_selected_secondary_area_id"),
            "feeder_area_strategy": runtime_context.get("feeder_area_strategy"),
            "grid_advisory_mode": runtime_context.get("grid_advisory_mode"),
            "grid_truth_level": runtime_context.get("grid_truth_level"),
            "grid_label_source_kind": runtime_context.get("grid_label_source_kind"),
            "offline_feeder_rl_adapter": bool(
                runtime_context.get("offline_feeder_rl_adapter", runtime_context.get("feeder_observation") is not None)
            ),
        }
        metadata.update(extra)
        return {key: value for key, value in metadata.items() if value is not None}

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


def _model_observation_size(model: Any) -> int | None:
    observation_space = getattr(model, "observation_space", None)
    if observation_space is None:
        policy = getattr(model, "policy", None)
        observation_space = getattr(policy, "observation_space", None)
    shape = getattr(observation_space, "shape", None)
    if not shape:
        return None
    try:
        return int(np.prod(shape))
    except Exception:
        return None


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


__all__ = [
    "DEFAULT_FEEDER_CHECKPOINT_PATH",
    "FeederActionPrediction",
    "FeederMaskablePPORuntimePolicy",
]
