"""Lightweight RL-preparation contracts kept independent of training frameworks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any


def _jsonify(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, dict):
        return {key: _jsonify(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    return value


@dataclass(frozen=True)
class ScenarioSeedSplit:
    train_start: int = 1000
    train_end: int = 1999
    validation_start: int = 2000
    validation_end: int = 2099
    test_start: int = 3000
    test_end: int = 3099

    def split_for_seed(self, seed: int) -> str:
        if self.train_start <= seed <= self.train_end:
            return "train"
        if self.validation_start <= seed <= self.validation_end:
            return "validation"
        if self.test_start <= seed <= self.test_end:
            return "test"
        raise ValueError(f"Seed {seed} is outside the configured RL seed ranges.")

    def bounds_for_split(self, split: str) -> tuple[int, int]:
        normalized = split.strip().lower()
        if normalized == "train":
            return self.train_start, self.train_end
        if normalized == "validation":
            return self.validation_start, self.validation_end
        if normalized == "test":
            return self.test_start, self.test_end
        raise ValueError(f"Unsupported split: {split}")

    def to_dict(self) -> dict[str, Any]:
        return _jsonify(asdict(self))


@dataclass(frozen=True)
class RLEpisodeScenario:
    scenario_id: str
    seed: int
    split: str
    start_ts: datetime
    duration_hours: int
    demand_level: str
    demand_multiplier: float
    request_count: int
    topology_scenario_id: str | None
    routing_provider_name: str = "simple_distance"
    dynamic_pricing_enabled: bool = True
    pricing_model: str = "dundee_tariff_dynamic"
    vehicle_mix_profile: str = "default"
    background_load_profile: str = "default"
    forecast_profile: str = "none"

    @property
    def end_ts(self) -> datetime:
        return self.start_ts + timedelta(hours=self.duration_hours)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["end_ts"] = self.end_ts
        return _jsonify(payload)


@dataclass(frozen=True)
class EvaluationMetrics:
    policy_name: str
    scenario_id: str
    seed: int
    request_count: int
    served_count: int
    missed_count: int
    invalid_action_count: int
    overload_attempt_count: int
    average_cost_gbp: float
    average_distance_km: float
    average_wait_minutes: float
    average_duration_minutes: float
    average_transformer_headroom_kw: float
    decision_latency_ms_mean: float

    def to_dict(self) -> dict[str, Any]:
        return _jsonify(asdict(self))


__all__ = [
    "EvaluationMetrics",
    "RLEpisodeScenario",
    "ScenarioSeedSplit",
]
