"""Recommendation policy interfaces for ranking candidate stations."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from ev_core.contracts.responses import RecommendationOption

from .ranker import CandidateContext


class RecommendationPolicy(Protocol):
    """Lightweight interface for ranking recommendation candidates."""

    name: str

    def rank(
        self,
        request: Any,
        candidates: Sequence[CandidateContext],
        runtime_context: dict[str, Any] | None = None,
    ) -> list[RecommendationOption]:
        """Return ranked recommendation options for a request."""


__all__ = ["RecommendationPolicy"]

