"""Small helpers for producing stable RL evaluation metrics."""

from __future__ import annotations

from typing import Iterable

from .contracts import EvaluationMetrics, RLEpisodeScenario


def mean_or_zero(values: Iterable[float]) -> float:
    values_list = [float(value) for value in values]
    if not values_list:
        return 0.0
    return sum(values_list) / len(values_list)


def build_evaluation_metrics(
    *,
    policy_name: str,
    scenario: RLEpisodeScenario,
    request_count: int,
    served_count: int,
    missed_count: int,
    invalid_action_count: int,
    overload_attempt_count: int,
    costs_gbp: list[float],
    distances_km: list[float],
    waits_minutes: list[float],
    durations_minutes: list[float],
    headroom_kw: list[float],
    decision_latency_ms: list[float],
) -> EvaluationMetrics:
    return EvaluationMetrics(
        policy_name=policy_name,
        scenario_id=scenario.scenario_id,
        seed=scenario.seed,
        request_count=request_count,
        served_count=served_count,
        missed_count=missed_count,
        invalid_action_count=invalid_action_count,
        overload_attempt_count=overload_attempt_count,
        average_cost_gbp=round(mean_or_zero(costs_gbp), 3),
        average_distance_km=round(mean_or_zero(distances_km), 3),
        average_wait_minutes=round(mean_or_zero(waits_minutes), 3),
        average_duration_minutes=round(mean_or_zero(durations_minutes), 3),
        average_transformer_headroom_kw=round(mean_or_zero(headroom_kw), 3),
        decision_latency_ms_mean=round(mean_or_zero(decision_latency_ms), 3),
    )


__all__ = ["build_evaluation_metrics", "mean_or_zero"]
