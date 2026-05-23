"""Placeholder forecast features for future RL observation builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ForecastFeatureSnapshot:
    expected_arrivals_next_1h: float = 0.0
    expected_kwh_next_1h: float = 0.0
    expected_transformer_load_next_1h: float = 0.0
    confidence: float = 0.0
    source: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


__all__ = ["ForecastFeatureSnapshot"]
