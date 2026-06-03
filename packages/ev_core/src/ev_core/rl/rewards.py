"""First-pass reward shaping for single-agent station-selection RL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RewardBreakdown:
    total: float
    served_reward: float
    invalid_penalty: float
    cost_penalty: float
    distance_penalty: float
    wait_penalty: float
    duration_penalty: float
    headroom_penalty: float
    missed_penalty: float

    def to_dict(self) -> dict[str, float]:
        return dict(asdict(self))


class StationSelectionReward:
    """Stable, documented reward constants for the PR3 environment skeleton."""

    VALID_SERVED_REWARD = 1.0
    INVALID_ACTION_PENALTY = -2.0
    MISSED_REQUEST_PENALTY = -1.5
    COST_SCALE_GBP = 50.0
    DISTANCE_SCALE_KM = 20.0
    WAIT_SCALE_MINUTES = 120.0
    DURATION_SCALE_MINUTES = 240.0
    LOW_HEADROOM_THRESHOLD_KW = 25.0
    LOW_HEADROOM_MAX_PENALTY = 0.75

    def compute(
        self,
        *,
        selected_option: Any | None = None,
        invalid_action: bool = False,
        missed: bool = False,
    ) -> RewardBreakdown:
        if invalid_action:
            return RewardBreakdown(
                total=self.INVALID_ACTION_PENALTY,
                served_reward=0.0,
                invalid_penalty=self.INVALID_ACTION_PENALTY,
                cost_penalty=0.0,
                distance_penalty=0.0,
                wait_penalty=0.0,
                duration_penalty=0.0,
                headroom_penalty=0.0,
                missed_penalty=0.0,
            )
        if missed or selected_option is None:
            return RewardBreakdown(
                total=self.MISSED_REQUEST_PENALTY,
                served_reward=0.0,
                invalid_penalty=0.0,
                cost_penalty=0.0,
                distance_penalty=0.0,
                wait_penalty=0.0,
                duration_penalty=0.0,
                headroom_penalty=0.0,
                missed_penalty=self.MISSED_REQUEST_PENALTY,
            )

        cost_penalty = -max(float(getattr(selected_option, "estimated_cost_gbp", 0.0)), 0.0) / self.COST_SCALE_GBP
        distance_penalty = -max(float(getattr(selected_option, "distance_km", 0.0)), 0.0) / self.DISTANCE_SCALE_KM
        wait_penalty = -max(float(getattr(selected_option, "estimated_wait_minutes", 0.0)), 0.0) / self.WAIT_SCALE_MINUTES
        duration_penalty = -max(float(getattr(selected_option, "estimated_duration_minutes", 0.0)), 0.0) / self.DURATION_SCALE_MINUTES
        headroom_penalty = self._headroom_penalty(float(getattr(selected_option, "transformer_headroom_kw", 0.0)))
        total = (
            self.VALID_SERVED_REWARD
            + cost_penalty
            + distance_penalty
            + wait_penalty
            + duration_penalty
            + headroom_penalty
        )
        return RewardBreakdown(
            total=round(float(total), 6),
            served_reward=self.VALID_SERVED_REWARD,
            invalid_penalty=0.0,
            cost_penalty=round(float(cost_penalty), 6),
            distance_penalty=round(float(distance_penalty), 6),
            wait_penalty=round(float(wait_penalty), 6),
            duration_penalty=round(float(duration_penalty), 6),
            headroom_penalty=round(float(headroom_penalty), 6),
            missed_penalty=0.0,
        )

    def _headroom_penalty(self, headroom_kw: float) -> float:
        if headroom_kw >= self.LOW_HEADROOM_THRESHOLD_KW:
            return 0.0
        shortfall_ratio = max(self.LOW_HEADROOM_THRESHOLD_KW - max(headroom_kw, 0.0), 0.0) / self.LOW_HEADROOM_THRESHOLD_KW
        return -min(shortfall_ratio * self.LOW_HEADROOM_MAX_PENALTY, self.LOW_HEADROOM_MAX_PENALTY)


__all__ = ["RewardBreakdown", "StationSelectionReward"]
