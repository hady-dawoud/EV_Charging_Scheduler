"""Pure, bounded safety scoring for grid advisory responses."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ev_core.config.recommendation import (
    RecommendationConfig,
    recommendation_config_from_env,
)
from ev_core.contracts.responses import RecommendationOption

from .baseline_policies import (
    CheapestPolicy,
    ClosestPolicy,
    FastestPolicy,
    WeightedScorePolicy,
)
from .feeder_rl_policy import FeederMaskablePPORuntimePolicy
from .policies import RecommendationPolicy
from .ranker import CandidateContext, RecommendationInput


CURTAILMENT_RISK_SCALE_KW = 22.0
SAFE_PENALTY_LIMIT = 0.25
RISKY_PENALTY_LIMIT = 0.60
REQUIRED_FEEDER_CONTEXT_KEYS = (
    "feeder_observation",
    "feeder_action_mask",
    "feeder_station_ids",
    "grid_advisories",
)


@dataclass(frozen=True)
class AdvisorySafety:
    penalty: float
    score: float
    status: str
    reason: str
    block_eligible: bool
    components: dict[str, float]


@dataclass(frozen=True)
class CandidateFeederMapping:
    candidate_station_id: str
    feeder_station_id: str | None
    action_index: int | None
    mapping_kind: str
    physical_claim: bool
    reason: str
    warning: str | None = None


@dataclass(frozen=True)
class CandidateSafety:
    station_id: str
    status: str
    score: float
    penalty: float
    reason: str
    blocked: bool
    mapping: CandidateFeederMapping
    advisory: AdvisorySafety
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SafetyFilterResult:
    options: tuple[RecommendationOption, ...]
    enabled: bool
    applied: bool
    mode: str
    mapping_mode: str
    penalized_count: int
    blocked_count: int
    fallback_used: bool
    reason: str


@dataclass(frozen=True)
class RLSafetyFilterConfig:
    enabled: bool = False
    mode: str = "penalty"
    strict: bool = False
    penalty_weight: float = 0.25
    block_unsafe: bool = False
    mapping_mode: str = "exact_only"
    fail_closed: bool = False


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(max(float(value), low), high)


def classify_safety_status(penalty: float) -> str:
    bounded = clamp(penalty)
    if bounded < SAFE_PENALTY_LIMIT:
        return "safe"
    if bounded < RISKY_PENALTY_LIMIT:
        return "caution"
    return "risky"


def _value(advisory: object, name: str, default: Any) -> Any:
    try:
        if isinstance(advisory, Mapping):
            return advisory.get(name, default)
        return getattr(advisory, name, default)
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return converted if math.isfinite(converted) else default


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        converted = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return converted


def _as_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return default


def advisory_safety(advisory: object | None) -> AdvisorySafety:
    if advisory is None:
        return AdvisorySafety(
            penalty=0.0,
            score=1.0,
            status="unavailable",
            reason="grid_advisory_unavailable",
            block_eligible=False,
            components={},
        )
    components = {
        "stress_risk": clamp(_as_float(_value(advisory, "stress_score", 0.0))),
        "voltage_risk": float(
            _as_int(_value(advisory, "voltage_violation_count", 0)) > 0
        ),
        "line_risk": float(_as_int(_value(advisory, "line_overload_count", 0)) > 0),
        "transformer_risk": float(
            _as_int(_value(advisory, "trafo_overload_count", 0)) > 0
        ),
        "opf_risk": float(
            not _as_bool(_value(advisory, "opf_feasible", True), default=True)
        ),
        "curtailment_risk": clamp(
            _as_float(_value(advisory, "curtailment_required_kw", 0.0))
            / CURTAILMENT_RISK_SCALE_KW
        ),
    }
    risk = clamp(
        0.30 * components["stress_risk"]
        + 0.15 * components["voltage_risk"]
        + 0.15 * components["line_risk"]
        + 0.15 * components["transformer_risk"]
        + 0.15 * components["opf_risk"]
        + 0.10 * components["curtailment_risk"]
    )
    verdict = str(_value(advisory, "verdict", "")).upper()
    risk_class = str(_value(advisory, "risk_class", "")).upper()
    block_eligible = (
        verdict == "REJECT"
        or risk_class == "VIOLATION"
        or components["opf_risk"] == 1.0
    )
    return AdvisorySafety(
        penalty=risk,
        score=1.0 - risk,
        status=classify_safety_status(risk),
        reason="recorded_grid_advisory",
        block_eligible=block_eligible,
        components=components,
    )


def map_candidates_to_feeder(
    *,
    candidate_station_ids: Sequence[str],
    feeder_station_ids: Sequence[str],
    feeder_action_mask: Sequence[bool],
    mapping_mode: str,
    documented_mapping: Mapping[str, str] | None = None,
) -> dict[str, CandidateFeederMapping]:
    station_ids = [str(value) for value in feeder_station_ids]
    valid_pairs = sorted(
        (
            (station_id, index)
            for index, (station_id, allowed) in enumerate(
                zip(station_ids, feeder_action_mask)
            )
            if bool(allowed)
        ),
        key=lambda item: (item[0], item[1]),
    )
    valid_by_id = {station_id: index for station_id, index in valid_pairs}
    documented = {
        str(candidate_id): str(feeder_id)
        for candidate_id, feeder_id in (documented_mapping or {}).items()
    }
    result: dict[str, CandidateFeederMapping] = {}
    unmatched: list[str] = []
    for candidate_id in sorted(str(value) for value in candidate_station_ids):
        mapped_id = (
            candidate_id
            if candidate_id in valid_by_id
            else documented.get(candidate_id)
        )
        if mapped_id in valid_by_id:
            result[candidate_id] = CandidateFeederMapping(
                candidate_station_id=candidate_id,
                feeder_station_id=mapped_id,
                action_index=valid_by_id[mapped_id],
                mapping_kind="exact",
                physical_claim=True,
                reason="exact_or_documented_candidate_feeder_mapping",
            )
        else:
            unmatched.append(candidate_id)
    if mapping_mode == "stable_ordinal_demo_bridge" and valid_pairs:
        for ordinal, candidate_id in enumerate(unmatched):
            feeder_id, action_index = valid_pairs[ordinal % len(valid_pairs)]
            result[candidate_id] = CandidateFeederMapping(
                candidate_station_id=candidate_id,
                feeder_station_id=feeder_id,
                action_index=action_index,
                mapping_kind="stable_ordinal_demo_bridge",
                physical_claim=False,
                reason="stable_ordinal_nonphysical_demo_mapping",
                warning="nonphysical_demo_mapping",
            )
    else:
        for candidate_id in unmatched:
            result[candidate_id] = CandidateFeederMapping(
                candidate_station_id=candidate_id,
                feeder_station_id=None,
                action_index=None,
                mapping_kind="unmapped",
                physical_claim=False,
                reason="no_candidate_feeder_mapping",
            )
    return result


def _mapping_metadata(
    mapping: CandidateFeederMapping,
    shared_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "rl_safety_mapping_kind": mapping.mapping_kind,
        "rl_safety_mapping_physical_claim": mapping.physical_claim,
        "rl_safety_mapping_warning": mapping.warning,
        "rl_safety_reason": mapping.reason,
        "rl_mapped_feeder_station_id": mapping.feeder_station_id,
        "rl_mapped_feeder_action_index": mapping.action_index,
        "rl_selected_feeder_station_id": shared_metadata.get(
            "rl_selected_feeder_station_id"
        ),
        "rl_selected_action_index": shared_metadata.get(
            "rl_selected_action_index"
        ),
        "feeder_selected_secondary_area_id": shared_metadata.get(
            "feeder_selected_secondary_area_id"
        ),
        "feeder_area_strategy": shared_metadata.get("feeder_area_strategy"),
        "feeder_valid_action_count": shared_metadata.get(
            "feeder_valid_action_count"
        ),
        "grid_truth_level": shared_metadata.get("grid_truth_level"),
        "grid_label_source_kind": shared_metadata.get(
            "grid_label_source_kind"
        ),
        "offline_feeder_rl_adapter": (
            mapping.mapping_kind == "stable_ordinal_demo_bridge"
        ),
    }


def _safety_metadata(
    *,
    base_score: float,
    mode: str,
    penalty_weight: float,
    status: str,
    score: float,
    penalty: float,
    adjusted_score: float,
    blocked: bool,
    reason: str,
    fallback_used: bool,
    mapping_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "rl_safety_mapping_kind": None,
        "rl_safety_mapping_physical_claim": None,
        "rl_safety_mapping_warning": None,
        "rl_mapped_feeder_station_id": None,
        "rl_mapped_feeder_action_index": None,
        "rl_selected_feeder_station_id": None,
        "rl_selected_action_index": None,
        "feeder_selected_secondary_area_id": None,
        "feeder_area_strategy": None,
        "feeder_valid_action_count": None,
        "grid_truth_level": None,
        "grid_label_source_kind": None,
        "offline_feeder_rl_adapter": None,
    }
    metadata.update(mapping_metadata or {})
    metadata.update(
        {
            "base_preference_score": base_score,
            "rl_safety_filter_enabled": True,
            "rl_safety_filter_mode": mode,
            "rl_safety_status": status,
            "rl_safety_score": clamp(score),
            "rl_safety_penalty": clamp(penalty),
            "rl_safety_penalty_weight": clamp(penalty_weight),
            "rl_safety_adjusted_score": adjusted_score,
            "rl_safety_blocked": blocked,
            "rl_safety_reason": reason,
            "fallback_used": fallback_used,
        }
    )
    return metadata


def apply_safety_to_options(
    *,
    base_options: Sequence[RecommendationOption],
    safety_by_station: Mapping[str, CandidateSafety],
    penalty_weight: float,
    mode: str,
    block_unsafe: bool,
    fail_closed: bool,
    mapping_mode: str = "exact_only",
) -> SafetyFilterResult:
    bounded_weight = clamp(penalty_weight)
    adjusted: list[RecommendationOption] = []
    blocked_count = 0
    penalized_count = 0
    for option in base_options:
        safety = safety_by_station[option.station_id]
        should_block = bool(
            safety.blocked and (mode == "block" or block_unsafe)
        )
        if should_block:
            blocked_count += 1
            continue
        base_score = float(option.score)
        bounded_penalty = clamp(safety.penalty)
        adjusted_score = base_score - bounded_weight * bounded_penalty
        if bounded_penalty > 0.0 and bounded_weight > 0.0:
            penalized_count += 1
        metadata = {
            **option.metadata,
            **_safety_metadata(
                base_score=base_score,
                mode=mode,
                penalty_weight=bounded_weight,
                status=safety.status,
                score=safety.score,
                penalty=bounded_penalty,
                adjusted_score=adjusted_score,
                blocked=False,
                reason=safety.reason,
                fallback_used=False,
                mapping_metadata=safety.metadata,
            ),
        }
        adjusted.append(
            option.model_copy(
                update={
                    "score": adjusted_score,
                    "metadata": metadata,
                }
            )
        )
    if not adjusted and blocked_count and not fail_closed:
        restored = tuple(
            option.model_copy(
                update={
                    "metadata": {
                        **option.metadata,
                        **_safety_metadata(
                            base_score=float(option.score),
                            mode=mode,
                            penalty_weight=bounded_weight,
                            status="unavailable",
                            score=safety_by_station[option.station_id].score,
                            penalty=safety_by_station[option.station_id].penalty,
                            adjusted_score=float(option.score),
                            blocked=False,
                            reason="all_candidates_blocked_fail_open",
                            fallback_used=True,
                            mapping_metadata=safety_by_station[
                                option.station_id
                            ].metadata,
                        ),
                        "rl_safety_filter_fallback_used": True,
                        "rl_safety_filter_reason": (
                            "all_candidates_blocked_fail_open"
                        ),
                    }
                }
            )
            for option in base_options
        )
        return SafetyFilterResult(
            options=restored,
            enabled=True,
            applied=False,
            mode=mode,
            mapping_mode=mapping_mode,
            penalized_count=0,
            blocked_count=blocked_count,
            fallback_used=True,
            reason="all_candidates_blocked_fail_open",
        )
    ranked = tuple(
        sorted(
            adjusted,
            key=lambda item: item.score,
            reverse=True,
        )
    )
    return SafetyFilterResult(
        options=ranked,
        enabled=True,
        applied=bool(penalized_count or blocked_count),
        mode=mode,
        mapping_mode=mapping_mode,
        penalized_count=penalized_count,
        blocked_count=blocked_count,
        fallback_used=False,
        reason="rl_safety_filter_applied",
    )


def safety_config_from_recommendation(
    config: RecommendationConfig,
    *,
    explicit_hybrid: bool,
) -> RLSafetyFilterConfig:
    return RLSafetyFilterConfig(
        enabled=bool(config.rl_safety_filter_enabled or explicit_hybrid),
        mode=config.rl_safety_filter_mode,
        strict=config.rl_safety_filter_strict,
        penalty_weight=config.rl_safety_filter_penalty_weight,
        block_unsafe=config.rl_safety_block_unsafe,
        mapping_mode=config.rl_safety_mapping_mode,
        fail_closed=bool(
            config.rl_safety_filter_strict
            or config.rl_policy_fail_closed
        ),
    )


def build_candidate_safety(
    *,
    candidate_station_ids: Sequence[str],
    mappings: Mapping[str, CandidateFeederMapping],
    grid_advisories: Mapping[str, object],
    selected_feeder_station_id: str | None,
    shared_metadata: Mapping[str, Any],
) -> dict[str, CandidateSafety]:
    result: dict[str, CandidateSafety] = {}
    for candidate_id in candidate_station_ids:
        mapping = mappings[candidate_id]
        if mapping.feeder_station_id is None:
            unavailable = advisory_safety(None)
            result[candidate_id] = CandidateSafety(
                station_id=candidate_id,
                status="unmapped",
                score=1.0,
                penalty=0.0,
                reason="no_candidate_feeder_mapping",
                blocked=False,
                mapping=mapping,
                advisory=unavailable,
                metadata=_mapping_metadata(mapping, shared_metadata),
            )
            continue
        advisory = advisory_safety(
            grid_advisories.get(mapping.feeder_station_id)
        )
        selected = mapping.feeder_station_id == selected_feeder_station_id
        reason = (
            "checkpoint_selected_recorded_advisory"
            if selected and advisory.status != "unavailable"
            else advisory.reason
        )
        result[candidate_id] = CandidateSafety(
            station_id=candidate_id,
            status=advisory.status,
            score=advisory.score,
            penalty=advisory.penalty,
            reason=reason,
            blocked=advisory.block_eligible,
            mapping=mapping,
            advisory=advisory,
            metadata=_mapping_metadata(mapping, shared_metadata),
        )
    return result


class RLSafetyPreferencePolicy:
    name = "rl_safety_preference"

    def __init__(
        self,
        *,
        base_policy: RecommendationPolicy | None = None,
        config: RLSafetyFilterConfig | None = None,
        feeder_policy: FeederMaskablePPORuntimePolicy | None = None,
    ) -> None:
        self.base_policy = base_policy
        self.config = config or safety_config_from_recommendation(
            recommendation_config_from_env(),
            explicit_hybrid=True,
        )
        self.feeder_policy = feeder_policy or FeederMaskablePPORuntimePolicy()
        self.last_diagnostics: dict[str, Any] = {}

    def _base_policy(self, preference_mode: str) -> RecommendationPolicy:
        if self.base_policy is not None:
            return self.base_policy
        policies: dict[str, RecommendationPolicy] = {
            "closest": ClosestPolicy(),
            "cheapest": CheapestPolicy(),
            "fastest": FastestPolicy(),
            "weighted_score": WeightedScorePolicy(),
        }
        return policies.get(preference_mode, WeightedScorePolicy())

    def rank(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        runtime_context = runtime_context or {}
        base_policy = self._base_policy(request.preference_mode)
        base_options = base_policy.rank(
            request,
            candidates,
            runtime_context=runtime_context,
        )
        final_ranker = base_policy.name
        missing_context_reason = _missing_context_reason(runtime_context)
        if missing_context_reason is not None:
            return self._prediction_unavailable_result(
                base_options,
                final_ranker=final_ranker,
                error=missing_context_reason,
            )
        prediction = self.feeder_policy.predict_feeder_action(runtime_context)
        if not prediction.available:
            return self._prediction_unavailable_result(
                base_options,
                final_ranker=final_ranker,
                error=prediction.error or "feeder_policy_unavailable",
            )

        station_ids = [
            str(value)
            for value in runtime_context.get("feeder_station_ids", [])
        ]
        action_mask = runtime_context.get("feeder_action_mask") or []
        mappings = map_candidates_to_feeder(
            candidate_station_ids=[
                str(candidate.station_id)
                for candidate in candidates
            ],
            feeder_station_ids=station_ids,
            feeder_action_mask=action_mask,
            mapping_mode=self.config.mapping_mode,
            documented_mapping=runtime_context.get(
                "candidate_feeder_station_map"
            ),
        )
        shared_metadata = {
            **runtime_context,
            "rl_selected_feeder_station_id": prediction.station_id,
            "rl_selected_action_index": prediction.action_index,
        }
        advisories = runtime_context.get("grid_advisories")
        safety_by_station = build_candidate_safety(
            candidate_station_ids=[
                str(candidate.station_id)
                for candidate in candidates
            ],
            mappings=mappings,
            grid_advisories=(
                advisories
                if isinstance(advisories, Mapping)
                else {}
            ),
            selected_feeder_station_id=prediction.station_id,
            shared_metadata=shared_metadata,
        )
        if safety_by_station and all(
            safety.status == "unavailable"
            for safety in safety_by_station.values()
        ):
            return self._safety_unavailable_result(
                base_options,
                safety_by_station=safety_by_station,
                final_ranker=final_ranker,
                error="grid_advisory_unavailable",
            )
        filter_result = apply_safety_to_options(
            base_options=base_options,
            safety_by_station=safety_by_station,
            penalty_weight=self.config.penalty_weight,
            mode=self.config.mode,
            block_unsafe=self.config.block_unsafe,
            fail_closed=self.config.fail_closed,
            mapping_mode=self.config.mapping_mode,
        )
        self.last_diagnostics = {
            "rl_safety_filter_enabled": self.config.enabled,
            "rl_safety_filter_applied": filter_result.applied,
            "rl_safety_filter_mode": self.config.mode,
            "rl_safety_mapping_mode": self.config.mapping_mode,
            "rl_safety_filter_penalized_count": (
                filter_result.penalized_count
            ),
            "rl_safety_filter_blocked_count": filter_result.blocked_count,
            "rl_safety_filter_fallback_used": (
                filter_result.fallback_used
            ),
            "rl_safety_filter_reason": filter_result.reason,
            "rl_selected_feeder_station_id": prediction.station_id,
            "rl_selected_action_index": prediction.action_index,
            "final_ranker": final_ranker,
        }
        return self._with_final_metadata(
            filter_result.options,
            final_ranker=final_ranker,
        )

    def _prediction_unavailable_result(
        self,
        base_options: Sequence[RecommendationOption],
        *,
        final_ranker: str,
        error: str,
    ) -> list[RecommendationOption]:
        self.last_diagnostics = {
            "rl_safety_filter_enabled": self.config.enabled,
            "rl_safety_filter_applied": False,
            "rl_safety_filter_fallback_used": not self.config.fail_closed,
            "rl_safety_filter_reason": error,
            "final_ranker": final_ranker,
        }
        if self.config.fail_closed:
            return []
        unavailable = [
            option.model_copy(
                update={
                    "metadata": {
                        **option.metadata,
                        **_safety_metadata(
                            base_score=float(option.score),
                            mode=self.config.mode,
                            penalty_weight=self.config.penalty_weight,
                            status="unavailable",
                            score=1.0,
                            penalty=0.0,
                            adjusted_score=float(option.score),
                            blocked=False,
                            reason=error,
                            fallback_used=True,
                        ),
                    }
                }
            )
            for option in base_options
        ]
        return self._with_final_metadata(
            unavailable,
            final_ranker=final_ranker,
        )

    def _safety_unavailable_result(
        self,
        base_options: Sequence[RecommendationOption],
        *,
        safety_by_station: Mapping[str, CandidateSafety],
        final_ranker: str,
        error: str,
    ) -> list[RecommendationOption]:
        self.last_diagnostics = {
            "rl_safety_filter_enabled": self.config.enabled,
            "rl_safety_filter_applied": False,
            "rl_safety_filter_fallback_used": not self.config.fail_closed,
            "rl_safety_filter_reason": error,
            "final_ranker": final_ranker,
        }
        if self.config.fail_closed:
            return []
        options = [
            option.model_copy(
                update={
                    "metadata": {
                        **option.metadata,
                        **_safety_metadata(
                            base_score=float(option.score),
                            mode=self.config.mode,
                            penalty_weight=self.config.penalty_weight,
                            status="unavailable",
                            score=1.0,
                            penalty=0.0,
                            adjusted_score=float(option.score),
                            blocked=False,
                            reason=error,
                            fallback_used=True,
                            mapping_metadata=safety_by_station[
                                option.station_id
                            ].metadata,
                        ),
                    }
                }
            )
            for option in base_options
        ]
        return self._with_final_metadata(
            options,
            final_ranker=final_ranker,
        )

    def _with_final_metadata(
        self,
        options: Sequence[RecommendationOption],
        *,
        final_ranker: str,
    ) -> list[RecommendationOption]:
        return [
            option.model_copy(
                update={
                    "metadata": {
                        **option.metadata,
                        "final_ranker": final_ranker,
                        "rl_safety_policy_name": self.name,
                    }
                }
            )
            for option in options
        ]


class RLSafetyClosestPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_closest"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=ClosestPolicy(), **kwargs)


class RLSafetyCheapestPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_cheapest"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=CheapestPolicy(), **kwargs)


class RLSafetyFastestPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_fastest"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=FastestPolicy(), **kwargs)


class RLSafetyWeightedPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_weighted"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=WeightedScorePolicy(), **kwargs)


def _missing_context_reason(
    runtime_context: Mapping[str, Any],
) -> str | None:
    for key in REQUIRED_FEEDER_CONTEXT_KEYS:
        if runtime_context.get(key) is None:
            return f"{key}_missing"
    return None


__all__ = [
    "CURTAILMENT_RISK_SCALE_KW",
    "RISKY_PENALTY_LIMIT",
    "SAFE_PENALTY_LIMIT",
    "AdvisorySafety",
    "CandidateFeederMapping",
    "CandidateSafety",
    "RLSafetyCheapestPolicy",
    "RLSafetyClosestPolicy",
    "RLSafetyFastestPolicy",
    "RLSafetyFilterConfig",
    "RLSafetyPreferencePolicy",
    "RLSafetyWeightedPolicy",
    "SafetyFilterResult",
    "apply_safety_to_options",
    "advisory_safety",
    "build_candidate_safety",
    "clamp",
    "classify_safety_status",
    "map_candidates_to_feeder",
    "safety_config_from_recommendation",
]
