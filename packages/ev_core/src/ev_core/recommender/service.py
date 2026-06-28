"""Service layer for Dundee station recommendation orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ev_core.contracts.responses import RecommendationOption, RecommendationResponse

from .policies import RecommendationPolicy
from .policy_registry import PolicyRegistry
from .ranker import CandidateContext, CandidateRanker, RecommendationInput


class RecommendationService:
    """Standalone recommendation service kept separate from the current app/backend."""

    def __init__(
        self,
        ranker: CandidateRanker | None = None,
        *,
        policy_name: str | None = None,
        policy_registry: PolicyRegistry | None = None,
        policy: RecommendationPolicy | None = None,
    ) -> None:
        self.ranker = ranker
        self.policy_registry = policy_registry or PolicyRegistry()
        self.policy = policy or (None if ranker is not None else self.policy_registry.get(policy_name))

    def recommend(
        self,
        *,
        request_id: str,
        client_request_id: str | None,
        simulated_timestamp: datetime,
        zone_id: str | None,
        source_type: str,
        preference_mode: str,
        candidate_contexts: list[CandidateContext],
        policy_name: str | None = None,
        policy_selection_metadata: dict[str, Any] | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> RecommendationResponse:
        """Rank candidate stations and return a standalone response contract."""

        payload = RecommendationInput(
            request_id=request_id,
            preference_mode=preference_mode,
            candidates=tuple(candidate_contexts),
        )
        runtime_context_payload = {
            "simulated_timestamp": simulated_timestamp,
            **(runtime_context or {}),
        }
        ranked, ranking_metadata = self._rank(
            payload,
            candidate_contexts,
            runtime_context=runtime_context_payload,
            policy_name=policy_name,
        )
        forecast_metadata = _forecast_metadata_from_context(runtime_context_payload)
        if forecast_metadata:
            ranked = _with_option_metadata(ranked, forecast_metadata)
        metadata = dict(policy_selection_metadata or {})
        metadata.update(forecast_metadata)
        metadata.update(_normalized_ranking_metadata(ranking_metadata))
        metadata.setdefault("requested_policy_name", policy_name)
        metadata.setdefault("effective_policy_name", policy_name or (getattr(self.policy, "name", None) if self.policy is not None else PolicyRegistry.default_policy_name))
        metadata.setdefault("policy_source", "explicit_policy_parameter" if policy_name else "service_default")
        metadata.setdefault("preference_mode", preference_mode)
        metadata.setdefault("policy_override_used", policy_name is not None)
        top_recommendation = ranked[0] if ranked else None
        if top_recommendation is not None:
            top_metadata = dict(top_recommendation.metadata or {})
            if "dynamic_pricing_enabled" in top_metadata:
                metadata["dynamic_pricing_enabled"] = top_metadata[
                    "dynamic_pricing_enabled"
                ]
            if "fallback_used" in top_metadata:
                metadata.setdefault("fallback_used", top_metadata["fallback_used"])
        congestion_note = self._build_congestion_note(ranked)
        debug_summary = self._build_debug_summary(preference_mode, ranked)
        return RecommendationResponse(
            request_id=request_id,
            client_request_id=client_request_id,
            simulated_timestamp=simulated_timestamp,
            zone_id=zone_id,
            top_recommendation=top_recommendation,
            alternatives=ranked[1:4],
            congestion_note=congestion_note,
            debug_reasoning_summary=debug_summary,
            source_type=source_type,
            metadata=metadata,
        )

    def _build_congestion_note(self, ranked: list) -> str | None:
        if not ranked:
            return "No feasible station matched the request window and charger constraints."
        top = ranked[0]
        if top.estimated_wait_minutes > 30:
            return "Best option still carries notable waiting time because local capacity is constrained."
        if top.transformer_headroom_kw < 50:
            return "Best option is serviceable but the attached transformer is operating with limited headroom."
        return None

    def _build_debug_summary(self, preference_mode: str, ranked: list) -> str:
        if not ranked:
            return f"No recommendation could be produced for preference mode '{preference_mode}'."
        top = ranked[0]
        return (
            f"Ranked {len(ranked)} stations for preference '{preference_mode}'. "
            f"Top option {top.station_name} scored {top.score:.3f} with distance {top.distance_km:.2f} km, "
            f"wait {top.estimated_wait_minutes} min, and headroom {top.transformer_headroom_kw:.1f} kW."
        )

    def _rank(
        self,
        payload: RecommendationInput,
        candidate_contexts: list[CandidateContext],
        *,
        runtime_context: dict[str, Any] | None = None,
        policy_name: str | None = None,
    ) -> tuple[list[RecommendationOption], dict[str, Any]]:
        if policy_name is not None:
            policy = self.policy_registry.get(policy_name)
            ranked = policy.rank(
                payload,
                candidate_contexts,
                runtime_context=runtime_context,
            )
            return ranked, dict(getattr(policy, "last_diagnostics", {}) or {})
        if self.ranker is not None:
            return self.ranker.rank(payload), {}
        if self.policy is None:
            self.policy = self.policy_registry.get()
        ranked = self.policy.rank(
            payload,
            candidate_contexts,
            runtime_context=runtime_context,
        )
        return ranked, dict(getattr(self.policy, "last_diagnostics", {}) or {})


def _forecast_metadata_from_context(runtime_context: dict[str, Any]) -> dict[str, Any]:
    value = runtime_context.get("forecast_metadata")
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item
        for key, item in value.items()
        if str(key).startswith("forecast_")
    }


def _with_option_metadata(
    options: list[RecommendationOption],
    metadata: dict[str, Any],
) -> list[RecommendationOption]:
    return [
        option.model_copy(update={"metadata": {**option.metadata, **metadata}})
        for option in options
    ]


def _normalized_ranking_metadata(
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    metadata = dict(diagnostics)
    if "rl_safety_filter_penalized_count" in metadata:
        metadata.setdefault(
            "rl_safety_candidates_penalized",
            metadata["rl_safety_filter_penalized_count"],
        )
    if "rl_safety_filter_blocked_count" in metadata:
        metadata.setdefault(
            "rl_safety_candidates_blocked",
            metadata["rl_safety_filter_blocked_count"],
        )
    if metadata.get("rl_safety_filter_enabled") is True:
        metadata.setdefault("rl_safety_candidates_penalized", 0)
        metadata.setdefault("rl_safety_candidates_blocked", 0)
        if "rl_safety_filter_fallback_used" in metadata:
            metadata.setdefault(
                "fallback_used",
                metadata["rl_safety_filter_fallback_used"],
            )
    return metadata


__all__ = ["RecommendationService"]
