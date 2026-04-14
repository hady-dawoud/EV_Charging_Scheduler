"""Ranking placeholders for future station recommendation strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ev_core.contracts.schemas import RecommendationCandidate


@dataclass(frozen=True)
class RecommendationInput:
    """Input bundle passed to future ranking implementations."""

    request_id: str
    candidate_station_ids: tuple[str, ...] = field(default_factory=tuple)


class CandidateRanker(Protocol):
    """Protocol for future recommendation ranking strategies."""

    def rank(self, payload: RecommendationInput) -> list[RecommendationCandidate]:
        """Return ranked recommendation candidates for a single request."""


class PlaceholderRanker:
    """Stub ranker kept import-safe until scoring rules are implemented."""

    def rank(self, payload: RecommendationInput) -> list[RecommendationCandidate]:
        raise NotImplementedError("TODO: implement ranking behavior.")
