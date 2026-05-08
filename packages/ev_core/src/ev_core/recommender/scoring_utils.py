"""Shared scoring helpers for recommendation policies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ev_core.contracts.responses import RecommendationOption

if TYPE_CHECKING:
    from .ranker import CandidateContext


def clamp(value: float, low: float, high: float) -> float:
    """Bound a numeric value to an inclusive range."""

    return min(max(value, low), high)


def default_reason_tags(candidate: CandidateContext) -> list[str]:
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


def candidate_to_option(
    candidate: CandidateContext,
    *,
    score: float,
    reason_tags: list[str] | None = None,
) -> RecommendationOption:
    return RecommendationOption(
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
        reason_tags=reason_tags if reason_tags is not None else default_reason_tags(candidate),
        metadata=candidate.metadata,
    )


__all__ = ["candidate_to_option", "clamp", "default_reason_tags"]
