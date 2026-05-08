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
    ) -> RecommendationResponse:
        """Rank candidate stations and return a standalone response contract."""

        payload = RecommendationInput(
            request_id=request_id,
            preference_mode=preference_mode,
            candidates=tuple(candidate_contexts),
        )
        ranked = self._rank(
            payload,
            candidate_contexts,
            runtime_context={"simulated_timestamp": simulated_timestamp},
            policy_name=policy_name,
        )
        top_recommendation = ranked[0] if ranked else None
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
    ) -> list[RecommendationOption]:
        if policy_name is not None:
            return self.policy_registry.get(policy_name).rank(payload, candidate_contexts, runtime_context=runtime_context)
        if self.ranker is not None:
            return self.ranker.rank(payload)
        if self.policy is None:
            self.policy = self.policy_registry.get()
        return self.policy.rank(payload, candidate_contexts, runtime_context=runtime_context)


__all__ = ["RecommendationService"]
