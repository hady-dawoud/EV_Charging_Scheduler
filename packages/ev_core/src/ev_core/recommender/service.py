"""Service-layer placeholders for future recommendation orchestration."""

from __future__ import annotations

from ev_core.contracts.schemas import RecommendationCandidate

from .ranker import CandidateRanker, RecommendationInput


class RecommendationService:
    """Thin service shell kept separate from the current mocked API flow."""

    def __init__(self, ranker: CandidateRanker) -> None:
        self.ranker = ranker

    def recommend(self, payload: RecommendationInput) -> list[RecommendationCandidate]:
        """Produce recommendation results once integrations are defined."""

        raise NotImplementedError("TODO: implement recommendation orchestration.")
