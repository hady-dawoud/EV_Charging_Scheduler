"""Baseline recommendation policies built on existing rankers."""

from __future__ import annotations

from typing import Any, Sequence

from ev_core.contracts.responses import RecommendationOption

from .ranker import CandidateContext, RecommendationInput, WeightedHeuristicRanker


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


__all__ = ["WeightedScorePolicy"]

