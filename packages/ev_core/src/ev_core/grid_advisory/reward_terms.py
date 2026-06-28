"""Reward shaping terms derived from grid advisory responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GridRewardTerms:
    grid_ok_bonus: float = 0.0
    grid_cautious_penalty: float = 0.0
    grid_reject_penalty: float = 0.0
    grid_violation_penalty: float = 0.0
    grid_uncertainty_penalty: float = 0.0
    grid_stress_penalty: float = 0.0
    grid_delta_penalty: float = 0.0
    grid_opf_penalty: float = 0.0
    grid_curtailment_penalty: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.grid_ok_bonus
            + self.grid_cautious_penalty
            + self.grid_reject_penalty
            + self.grid_violation_penalty
            + self.grid_uncertainty_penalty
            + self.grid_stress_penalty
            + self.grid_delta_penalty
            + self.grid_opf_penalty
            + self.grid_curtailment_penalty
        )


def grid_reward_terms(advisory: Any | None) -> GridRewardTerms:
    """Convert advisory verdict/risk into soft RL reward terms."""

    if advisory is None or not bool(getattr(advisory, "advisory_available", False)):
        return GridRewardTerms()

    verdict = str(getattr(advisory, "verdict", "OK")).upper()
    risk_class = str(getattr(advisory, "risk_class", "SAFE")).upper()
    ok_bonus = 0.05 if verdict == "OK" and risk_class == "SAFE" else 0.0
    cautious_penalty = -0.2 if verdict == "CAUTIOUS" else 0.0
    reject_penalty = -0.8 if verdict == "REJECT" else 0.0
    violation_penalty = -1.2 if risk_class == "VIOLATION" else 0.0
    stress_penalty = -0.45 * max(min(_as_float(getattr(advisory, "stress_score", 0.0)), 1.0), 0.0)
    delta_v = abs(min(_as_float(getattr(advisory, "delta_v_min_pu", 0.0)), 0.0))
    line_delta = max(_as_float(getattr(advisory, "delta_max_line_loading_percent", 0.0)), 0.0) / 100.0
    trafo_delta = max(_as_float(getattr(advisory, "delta_max_trafo_loading_percent", 0.0)), 0.0) / 100.0
    delta_penalty = -min((delta_v * 5.0) + (line_delta * 0.35) + (trafo_delta * 0.35), 0.8)
    violation_count = (
        max(int(getattr(advisory, "voltage_violation_count", 0) or 0), 0)
        + max(int(getattr(advisory, "line_overload_count", 0) or 0), 0)
        + max(int(getattr(advisory, "trafo_overload_count", 0) or 0), 0)
    )
    if violation_count:
        violation_penalty -= min(0.35 * violation_count, 1.0)
    opf_penalty = -0.7 if not bool(getattr(advisory, "opf_feasible", True)) else 0.0
    curtailment_penalty = -min(max(_as_float(getattr(advisory, "opf_curtailment_kwh", 0.0)), 0.0) / 30.0, 0.8)
    uncertainty_penalty = 0.0
    if bool(getattr(advisory, "ood_flag", False)):
        uncertainty_penalty -= 0.2
    if bool(getattr(advisory, "uq_flag", False)):
        uncertainty_penalty -= 0.2
    return GridRewardTerms(
        grid_ok_bonus=ok_bonus,
        grid_cautious_penalty=cautious_penalty,
        grid_reject_penalty=reject_penalty,
        grid_violation_penalty=violation_penalty,
        grid_uncertainty_penalty=uncertainty_penalty,
        grid_stress_penalty=stress_penalty,
        grid_delta_penalty=delta_penalty,
        grid_opf_penalty=opf_penalty,
        grid_curtailment_penalty=curtailment_penalty,
    )


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = ["GridRewardTerms", "grid_reward_terms"]
