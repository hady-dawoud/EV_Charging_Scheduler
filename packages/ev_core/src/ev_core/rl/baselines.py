"""RL-specific baseline helpers that reuse the existing recommendation candidate path."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

from ev_core.contracts.responses import RecommendationOption


def _stable_index(seed_text: str, length: int) -> int:
    if length <= 0:
        return 0
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % length


@dataclass(frozen=True)
class RandomValidPolicy:
    """Select pseudo-randomly from already-feasible recommendation options only."""

    seed: int | str = 0

    def select_option(
        self,
        *,
        request_id: str,
        options: Sequence[RecommendationOption],
    ) -> RecommendationOption | None:
        if not options:
            return None
        index = _stable_index(f"{self.seed}|{request_id}", len(options))
        return list(options)[index]


__all__ = ["RandomValidPolicy"]
