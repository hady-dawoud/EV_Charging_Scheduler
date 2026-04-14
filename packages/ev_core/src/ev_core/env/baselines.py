"""Baseline policies for the Dundee standalone simulator runtime."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ev_core.contracts.responses import RecommendationOption

from .allocator import AllocationPolicy
from .entities import SimulationRequest

PolicyMode = str


def _stable_index(seed: str, length: int) -> int:
    """Return a stable deterministic index for repeatable pseudo-random choices."""

    if length <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % length


@dataclass(frozen=True)
class RandomPolicy(AllocationPolicy):
    """Stable pseudo-random policy for demo comparisons."""

    policy_mode: str = "random"

    def select_option(
        self,
        request: SimulationRequest,
        options: list[RecommendationOption],
    ) -> RecommendationOption | None:
        if not options:
            return None
        idx = _stable_index(request.request_id, len(options))
        return options[idx]


@dataclass(frozen=True)
class GreedyFastestServicePolicy(AllocationPolicy):
    """Choose the station with the shortest wait-plus-service estimate."""

    policy_mode: str = "greedy_fastest_service"

    def select_option(
        self,
        request: SimulationRequest,
        options: list[RecommendationOption],
    ) -> RecommendationOption | None:
        if not options:
            return None
        return min(
            options,
            key=lambda option: (
                option.estimated_wait_minutes + option.estimated_duration_minutes,
                -option.transformer_headroom_kw,
                option.distance_km,
            ),
        )


@dataclass(frozen=True)
class OverloadAwarePolicy(AllocationPolicy):
    """Prefer headroom and short waits to avoid synthetic transformer overloads."""

    policy_mode: str = "overload_aware"

    def select_option(
        self,
        request: SimulationRequest,
        options: list[RecommendationOption],
    ) -> RecommendationOption | None:
        if not options:
            return None
        return min(
            options,
            key=lambda option: (
                option.transformer_headroom_kw < 20.0,
                option.estimated_wait_minutes,
                -option.transformer_headroom_kw,
                option.distance_km,
            ),
        )


@dataclass(frozen=True)
class CostAwarePolicy(AllocationPolicy):
    """Prefer lower estimated cost while staying reasonably serviceable."""

    policy_mode: str = "cost_aware"

    def select_option(
        self,
        request: SimulationRequest,
        options: list[RecommendationOption],
    ) -> RecommendationOption | None:
        if not options:
            return None
        return min(
            options,
            key=lambda option: (
                option.estimated_cost_gbp,
                option.estimated_wait_minutes,
                -option.transformer_headroom_kw,
                option.distance_km,
            ),
        )


POLICY_REGISTRY: dict[str, AllocationPolicy] = {
    "random": RandomPolicy(),
    "greedy_fastest_service": GreedyFastestServicePolicy(),
    "overload_aware": OverloadAwarePolicy(),
    "cost_aware": CostAwarePolicy(),
}


def get_policy(policy_mode: str) -> AllocationPolicy:
    """Return the named Dundee simulator policy."""

    if policy_mode not in POLICY_REGISTRY:
        raise ValueError(f"Unsupported policy mode: {policy_mode}")
    return POLICY_REGISTRY[policy_mode]


__all__ = [
    "CostAwarePolicy",
    "GreedyFastestServicePolicy",
    "OverloadAwarePolicy",
    "POLICY_REGISTRY",
    "RandomPolicy",
    "get_policy",
]
