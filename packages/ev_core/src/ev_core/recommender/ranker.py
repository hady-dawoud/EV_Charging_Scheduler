"""Heuristic ranking strategies for Dundee station recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ev_core.contracts.responses import RecommendationOption


@dataclass(frozen=True)
class CandidateContext:
    """Raw recommendation features prepared before scoring."""

    station_id: str
    station_name: str
    zone_id: str
    transformer_id: str
    distance_km: float
    estimated_wait_minutes: int
    estimated_duration_minutes: int
    estimated_cost_gbp: float
    transformer_headroom_kw: float
    current_queue: int
    utilization: float
    charger_compatible: bool
    score_inputs: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class RecommendationInput:
    """Input bundle passed to the Dundee ranking implementation."""

    request_id: str
    preference_mode: str
    candidates: tuple[CandidateContext, ...] = field(default_factory=tuple)


class CandidateRanker(Protocol):
    """Protocol for recommendation ranking strategies."""

    def rank(self, payload: RecommendationInput) -> list[RecommendationOption]:
        """Return ranked recommendation candidates for a single request."""


class WeightedHeuristicRanker:
    """Weighted heuristic ranker aligned with the Dundee demo policies."""

    WEIGHTS = {
        "closest": {
            "distance": 0.45,
            "wait": 0.20,
            "headroom": 0.15,
            "price": 0.10,
            "duration": 0.05,
            "compatibility": 0.05,
        },
        "cheapest": {
            "price": 0.40,
            "distance": 0.15,
            "wait": 0.15,
            "headroom": 0.15,
            "duration": 0.10,
            "compatibility": 0.05,
        },
        "fastest": {
            "wait": 0.35,
            "duration": 0.25,
            "headroom": 0.20,
            "distance": 0.10,
            "price": 0.05,
            "compatibility": 0.05,
        },
    }

    def rank(self, payload: RecommendationInput) -> list[RecommendationOption]:
        weights = self.WEIGHTS.get(payload.preference_mode, self.WEIGHTS["fastest"])
        ranked: list[RecommendationOption] = []
        for candidate in payload.candidates:
            score = self._score_candidate(candidate, weights)
            reason_tags = self._reason_tags(candidate)
            ranked.append(
                RecommendationOption(
                    station_id=candidate.station_id,
                    station_name=candidate.station_name,
                    zone_id=candidate.zone_id,
                    transformer_id=candidate.transformer_id,
                    score=round(score, 4),
                    distance_km=round(candidate.distance_km, 3),
                    estimated_wait_minutes=int(candidate.estimated_wait_minutes),
                    estimated_duration_minutes=int(candidate.estimated_duration_minutes),
                    estimated_cost_gbp=round(candidate.estimated_cost_gbp, 3),
                    transformer_headroom_kw=round(candidate.transformer_headroom_kw, 3),
                    current_queue=int(candidate.current_queue),
                    utilization=round(candidate.utilization, 4),
                    charger_compatible=bool(candidate.charger_compatible),
                    reason_tags=reason_tags,
                    metadata=candidate.metadata,
                )
            )
        return sorted(
            ranked,
            key=lambda option: (-option.score, option.estimated_wait_minutes, option.distance_km, option.estimated_cost_gbp),
        )

    def _score_candidate(self, candidate: CandidateContext, weights: dict[str, float]) -> float:
        compatibility = 1.0 if candidate.charger_compatible else 0.0
        normalized_headroom = min(max(candidate.transformer_headroom_kw / 500.0, 0.0), 1.0)
        wait_component = 1.0 / (1.0 + (candidate.estimated_wait_minutes / 15.0))
        duration_component = 1.0 / (1.0 + (candidate.estimated_duration_minutes / 15.0))
        distance_component = 1.0 / (1.0 + candidate.distance_km)
        price_component = 1.0 / (1.0 + candidate.estimated_cost_gbp)
        return (
            weights["distance"] * distance_component
            + weights["wait"] * wait_component
            + weights["headroom"] * normalized_headroom
            + weights["price"] * price_component
            + weights["duration"] * duration_component
            + weights["compatibility"] * compatibility
        )

    def _reason_tags(self, candidate: CandidateContext) -> list[str]:
        tags: list[str] = []
        if candidate.distance_km <= 1.5:
            tags.append("nearby")
        if candidate.estimated_wait_minutes <= 15:
            tags.append("low_wait")
        if candidate.transformer_headroom_kw >= 100:
            tags.append("high_headroom")
        if candidate.estimated_cost_gbp <= 6.0:
            tags.append("low_cost")
        if candidate.charger_compatible:
            tags.append("charger_match")
        return tags[:4]


__all__ = [
    "CandidateContext",
    "CandidateRanker",
    "RecommendationInput",
    "WeightedHeuristicRanker",
]
