"""Scenario sampling for feeder-aligned public-EV station selection."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Sequence

from .contracts import FeederAction, FeederEpisodeScenario


class FeederScenarioSampler:
    """Sample deterministic feeder episodes from the exported action catalog."""

    def __init__(self, *, actions: Sequence[FeederAction], allowed_area_ids: Sequence[str] | None = None) -> None:
        self.actions = list(actions)
        available_area_ids = {action.secondary_area_id for action in self.actions}
        if allowed_area_ids is not None:
            requested_area_ids = {str(area_id) for area_id in allowed_area_ids}
            available_area_ids = available_area_ids.intersection(requested_area_ids)
        self.area_ids = sorted(available_area_ids)
        if not self.area_ids:
            raise ValueError("FeederScenarioSampler requires at least one secondary_area_id.")

    def sample(
        self,
        *,
        seed: int,
        split: str = "train",
        duration_hours: int = 1,
        request_count: int | None = None,
        request_prior_sources: Sequence[str] = ("dundee", "acn", "digitaltwin"),
        grid_evaluation_mode: str = "replay",
    ) -> FeederEpisodeScenario:
        rng = random.Random(seed)
        area_id = self.area_ids[rng.randrange(len(self.area_ids))]
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        hour = rng.choice([0, 7, 12, 17, 20])
        count = int(request_count if request_count is not None else max(1, min(24, len(self._actions_for_area(area_id)) * 2)))
        return FeederEpisodeScenario(
            scenario_id=f"feeder-rl-{split}-{seed}-{area_id.split(':')[-1]}-{duration_hours}h",
            seed=int(seed),
            split=split,
            secondary_area_id=area_id,
            start_ts=datetime(2024, month, day, hour, 0, 0),
            duration_hours=int(duration_hours),
            request_count=count,
            request_prior_sources=tuple(str(item) for item in request_prior_sources),
            grid_evaluation_mode=str(grid_evaluation_mode),
        )

    def _actions_for_area(self, area_id: str) -> list[FeederAction]:
        return [action for action in self.actions if action.secondary_area_id == area_id]


__all__ = ["FeederScenarioSampler"]
