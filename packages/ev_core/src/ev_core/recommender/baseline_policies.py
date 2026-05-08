"""Baseline recommendation policies built on existing rankers."""

from __future__ import annotations

from typing import Any, Sequence

from ev_core.contracts.responses import RecommendationOption

from .ranker import CandidateContext, RecommendationInput, WeightedHeuristicRanker
from .scoring_utils import candidate_to_option, clamp


class WeightedScorePolicy:
    """Default policy wrapper preserving the existing weighted heuristic output."""

    name = "weighted_score"

    def __init__(self, ranker: WeightedHeuristicRanker | None = None) -> None:
        self.ranker = ranker or WeightedHeuristicRanker()

    def rank(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        payload = RecommendationInput(
            request_id=request.request_id,
            preference_mode=request.preference_mode,
            candidates=tuple(candidates),
        )
        return self.ranker.rank(payload)


class _SingleScorePolicy:
    """Base class for transparent single-objective recommendation baselines."""

    name: str

    def rank(
        self,
        request: RecommendationInput,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        options = [candidate_to_option(candidate, score=self._score_candidate(candidate)) for candidate in candidates]
        return sorted(options, key=self._sort_key)

    def _score_candidate(self, candidate: CandidateContext) -> float:
        raise NotImplementedError

    def _sort_key(self, option: RecommendationOption) -> tuple:
        raise NotImplementedError

    def _compatibility_multiplier(self, candidate: CandidateContext) -> float:
        return 1.0 if candidate.charger_compatible else 0.0


class ClosestPolicy(_SingleScorePolicy):
    """Rank stations by nearest distance first."""

    name = "closest"

    def _score_candidate(self, candidate: CandidateContext) -> float:
        return self._compatibility_multiplier(candidate) * (1.0 / (1.0 + candidate.distance_km))

    def _sort_key(self, option: RecommendationOption) -> tuple:
        return (
            -option.score,
            option.estimated_wait_minutes,
            option.estimated_cost_gbp,
            -option.transformer_headroom_kw,
            option.station_id,
        )


class CheapestPolicy(_SingleScorePolicy):
    """Rank stations by lowest estimated charging cost first."""

    name = "cheapest"

    def _score_candidate(self, candidate: CandidateContext) -> float:
        return self._compatibility_multiplier(candidate) * (1.0 / (1.0 + candidate.estimated_cost_gbp))

    def _sort_key(self, option: RecommendationOption) -> tuple:
        return (
            -option.score,
            option.distance_km,
            option.estimated_wait_minutes,
            -option.transformer_headroom_kw,
            option.station_id,
        )


class FastestPolicy(_SingleScorePolicy):
    """Rank stations by the shortest wait plus charging duration."""

    name = "fastest"

    def _score_candidate(self, candidate: CandidateContext) -> float:
        total_time = candidate.estimated_wait_minutes + candidate.estimated_duration_minutes
        return self._compatibility_multiplier(candidate) * (1.0 / (1.0 + total_time / 15.0))

    def _sort_key(self, option: RecommendationOption) -> tuple:
        return (
            -option.score,
            option.estimated_wait_minutes,
            option.estimated_duration_minutes,
            option.distance_km,
            option.station_id,
        )


class OverloadAwarePolicy(_SingleScorePolicy):
    """Rank stations by grid headroom and low local congestion."""

    name = "overload_aware"

    def _score_candidate(self, candidate: CandidateContext) -> float:
        headroom_component = clamp(candidate.transformer_headroom_kw / 500.0, 0.0, 1.0)
        queue_component = 1.0 / (1.0 + candidate.current_queue)
        utilization_component = 1.0 - clamp(candidate.utilization, 0.0, 1.0)
        wait_component = 1.0 / (1.0 + candidate.estimated_wait_minutes / 15.0)
        score = (
            0.45 * headroom_component
            + 0.25 * utilization_component
            + 0.20 * queue_component
            + 0.10 * wait_component
        )
        return self._compatibility_multiplier(candidate) * score

    def _sort_key(self, option: RecommendationOption) -> tuple:
        return (
            -option.score,
            -option.transformer_headroom_kw,
            option.utilization,
            option.current_queue,
            option.distance_km,
            option.station_id,
        )


__all__ = [
    "CheapestPolicy",
    "ClosestPolicy",
    "FastestPolicy",
    "OverloadAwarePolicy",
    "WeightedScorePolicy",
]

