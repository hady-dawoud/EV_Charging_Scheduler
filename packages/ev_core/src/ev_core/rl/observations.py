"""Observation-building helpers for the first single-agent station-selection RL env."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Mapping

import numpy as np


CHARGER_PREFERENCE_ORDER = ("any", "ac", "rapid")


@dataclass(frozen=True)
class ObservationSpec:
    station_count: int
    feature_count: int
    vector_size: int


class ObservationBuilder:
    """Build a fixed-size flat observation vector from request and station features."""

    global_feature_count = 12
    station_feature_count = 9

    def __init__(self, *, station_ids: list[str]) -> None:
        self.station_ids = list(station_ids)
        self.spec = ObservationSpec(
            station_count=len(self.station_ids),
            feature_count=self.global_feature_count,
            vector_size=self.global_feature_count + (len(self.station_ids) * self.station_feature_count),
        )

    def build(
        self,
        *,
        request: Any | None,
        current_time: datetime | None,
        station_features: Mapping[str, Any],
        action_mask: list[bool],
    ) -> np.ndarray:
        if request is None or current_time is None:
            return np.zeros(self.spec.vector_size, dtype=np.float32)

        features: list[float] = []
        hour_fraction = float(current_time.hour + (current_time.minute / 60.0))
        angle = (hour_fraction / 24.0) * (2.0 * math.pi)
        features.extend([math.sin(angle), math.cos(angle)])
        slack_minutes = max((request.latest_finish_ts - request.request_timestamp).total_seconds() / 60.0, 0.0)
        features.extend(
            [
                float(request.requested_energy_kwh or 0.0),
                float(slack_minutes),
                *self._charger_preference_one_hot(getattr(request, "charger_type", "Any")),
                float(request.current_soc or 0.0),
                float(request.target_soc or 0.0),
                float(request.battery_kwh or 0.0),
                float(request.vehicle_max_ac_kw or 0.0),
                float(request.vehicle_max_dc_kw or 0.0),
            ]
        )
        for index, station_id in enumerate(self.station_ids):
            feature = station_features.get(station_id)
            features.extend(
                [
                    self._as_float(getattr(feature, "distance_km", 0.0)),
                    self._as_float(getattr(feature, "estimated_wait_minutes", 0.0)),
                    self._as_float(getattr(feature, "estimated_duration_minutes", 0.0)),
                    self._as_float(getattr(feature, "estimated_cost_gbp", 0.0)),
                    self._as_float(getattr(feature, "transformer_headroom_kw", 0.0)),
                    self._as_float(getattr(feature, "current_queue", 0.0)),
                    self._as_float(getattr(feature, "utilization", 0.0)),
                    1.0 if bool(getattr(feature, "charger_compatible", False)) else 0.0,
                    1.0 if bool(action_mask[index]) else 0.0,
                ]
            )
        return np.asarray(features, dtype=np.float32)

    def zeros(self) -> np.ndarray:
        return np.zeros(self.spec.vector_size, dtype=np.float32)

    def _charger_preference_one_hot(self, charger_type: str) -> list[float]:
        normalized = str(charger_type or "Any").strip().lower()
        if normalized in {"dc", "ultra_rapid", "ultrarapid"}:
            normalized = "rapid"
        return [1.0 if normalized == value else 0.0 for value in CHARGER_PREFERENCE_ORDER]

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(result):
            return 0.0
        return result


__all__ = ["ObservationBuilder", "ObservationSpec"]
