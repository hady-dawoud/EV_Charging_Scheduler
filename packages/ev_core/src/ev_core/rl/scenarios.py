"""Deterministic RL scenario sampling and Monte Carlo request generation."""

from __future__ import annotations

import calendar
import random
from datetime import datetime, timedelta
from typing import Any

from ev_core.analysis.rl_demand_realism import build_demand_realism_summary
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.utils.timebase import TIME_STEP_MINUTES, ceil_to_timebase, floor_to_timebase
from ev_core.vehicles.profiles import get_default_vehicle_profiles

from .contracts import RLEpisodeScenario, ScenarioSeedSplit


DEMAND_LEVELS = ("normal", "busy", "stress")
SUPPORTED_HORIZONS = (1, 3, 6, 24)
DEMAND_MULTIPLIER_BANDS = {
    "normal": (1.5, 3.0),
    "busy": (3.0, 5.0),
    "stress": (5.0, 6.5),
}


class RLScenarioSampler:
    """Build deterministic RL episode scenarios from fixed seed splits and demand guidance."""

    def __init__(
        self,
        *,
        bundle: Any,
        vehicle_profiles: dict[str, Any] | None = None,
        seed_split: ScenarioSeedSplit | None = None,
        routing_provider_name: str = "simple_distance",
    ) -> None:
        self.bundle = bundle
        self.vehicle_profiles = vehicle_profiles or get_default_vehicle_profiles()
        self.seed_split = seed_split or ScenarioSeedSplit()
        self.routing_provider_name = routing_provider_name
        self.demand_summary = build_demand_realism_summary(
            bundle=bundle,
            vehicle_profiles=self.vehicle_profiles,
        )

    def sample(
        self,
        *,
        seed: int,
        split: str | None = None,
        duration_hours: int | None = None,
        demand_level: str | None = None,
    ) -> RLEpisodeScenario:
        scenario_split = split or self.seed_split.split_for_seed(seed)
        if split is not None and self.seed_split.split_for_seed(seed) != split:
            raise ValueError(f"Seed {seed} does not belong to split '{split}'.")

        rng = random.Random(seed)
        horizon = int(duration_hours or rng.choice(SUPPORTED_HORIZONS))
        if horizon not in SUPPORTED_HORIZONS:
            raise ValueError(f"Unsupported duration_hours: {duration_hours}")
        level = str(demand_level or self._sample_demand_level(rng))
        if level not in DEMAND_LEVELS:
            raise ValueError(f"Unsupported demand_level: {demand_level}")

        request_range = self.get_request_count_range(duration_hours=horizon, demand_level=level)
        request_count = rng.randint(request_range["min_requests"], request_range["max_requests"])
        multiplier_low, multiplier_high = DEMAND_MULTIPLIER_BANDS[level]
        demand_multiplier = round(rng.uniform(multiplier_low, multiplier_high), 3)
        start_ts = self._sample_start_timestamp(rng, duration_hours=horizon)
        topology_scenario_id = self._sample_topology_scenario_id(rng, demand_level=level)
        scenario_id = f"rl-{scenario_split}-{seed}-{start_ts.strftime('%Y%m%dT%H%M')}-{horizon}h-{level}"

        return RLEpisodeScenario(
            scenario_id=scenario_id,
            seed=seed,
            split=scenario_split,
            start_ts=start_ts,
            duration_hours=horizon,
            demand_level=level,
            demand_multiplier=demand_multiplier,
            request_count=request_count,
            topology_scenario_id=topology_scenario_id,
            routing_provider_name=self.routing_provider_name,
            dynamic_pricing_enabled=True,
            pricing_model="dundee_tariff_dynamic",
            vehicle_mix_profile="default",
            background_load_profile="default",
            forecast_profile="none",
        )

    def sample_many(
        self,
        *,
        split: str,
        count: int,
        duration_hours: int | None = None,
        demand_level: str | None = None,
    ) -> list[RLEpisodeScenario]:
        start_seed, end_seed = self.seed_split.bounds_for_split(split)
        limit = max(min(int(count), (end_seed - start_seed) + 1), 0)
        return [
            self.sample(
                seed=seed,
                split=split,
                duration_hours=duration_hours,
                demand_level=demand_level,
            )
            for seed in range(start_seed, start_seed + limit)
        ]

    def get_request_count_range(self, *, duration_hours: int, demand_level: str) -> dict[str, int]:
        horizon_ranges = self.demand_summary["scenario_request_ranges"]
        return dict(horizon_ranges[int(duration_hours)][str(demand_level)])

    def _sample_demand_level(self, rng: random.Random) -> str:
        bucket = rng.random()
        if bucket < 0.55:
            return "normal"
        if bucket < 0.90:
            return "busy"
        return "stress"

    def _sample_topology_scenario_id(self, rng: random.Random, *, demand_level: str) -> str | None:
        if demand_level == "stress":
            return "dundee_synthetic_v1_stress" if rng.random() < 0.35 else "dundee_synthetic_v1_realistic"
        if demand_level == "busy":
            return "dundee_synthetic_v1_realistic"
        return "dundee_synthetic_v1_realistic" if rng.random() < 0.8 else None

    def _sample_start_timestamp(self, rng: random.Random, *, duration_hours: int) -> datetime:
        month = rng.randint(1, 12)
        want_weekend = rng.random() < 0.3
        day = self._pick_day_in_month(year=2024, month=month, want_weekend=want_weekend, occurrence=(rng.randint(0, 3)))
        hour_choices = {
            1: (0, 8, 12, 17, 20),
            3: (0, 9, 12, 15, 18, 21),
            6: (0, 6, 12, 18),
            24: (0,),
        }
        hour = rng.choice(hour_choices[duration_hours])
        return datetime(2024, month, day, hour, 0, 0)

    def _pick_day_in_month(self, *, year: int, month: int, want_weekend: bool, occurrence: int) -> int:
        matching_days: list[int] = []
        _, days_in_month = calendar.monthrange(year, month)
        for day in range(1, days_in_month + 1):
            weekday = datetime(year, month, day).weekday()
            is_weekend = weekday >= 5
            if is_weekend == want_weekend:
                matching_days.append(day)
        if not matching_days:
            return 1
        return matching_days[min(occurrence, len(matching_days) - 1)]


def generate_requests_for_scenario(
    scenario: RLEpisodeScenario,
    *,
    request_generator: SyntheticLiveRequestGenerator,
) -> list[ExternalChargingRequest]:
    """Generate deterministic synthetic-live requests scoped to one sampled RL scenario."""

    seeded_generator = SyntheticLiveRequestGenerator(
        request_generator_params=request_generator.request_generator_params,
        stations=request_generator.stations,
        vehicle_profiles=request_generator.vehicle_profiles,
        seed=f"{request_generator.seed}|scenario:{scenario.seed}",
    )
    end_ts = scenario.end_ts - timedelta(minutes=TIME_STEP_MINUTES)
    requests = seeded_generator.generate_batch(
        start_ts=scenario.start_ts,
        end_ts=max(end_ts, scenario.start_ts),
        count=scenario.request_count,
    )

    scenario_requests: list[ExternalChargingRequest] = []
    for index, request in enumerate(requests, start=1):
        metadata = dict(request.metadata or {})
        metadata.update(
            {
                "scenario_id": scenario.scenario_id,
                "scenario_seed": scenario.seed,
                "split": scenario.split,
                "demand_level": scenario.demand_level,
                "demand_multiplier": scenario.demand_multiplier,
                "rl_request_index": index,
            }
        )
        request_ts = min(max(request.request_timestamp, scenario.start_ts), end_ts if end_ts >= scenario.start_ts else scenario.start_ts)
        latest_finish_ts = min(
            ceil_to_timebase(request.latest_finish_ts),
            ceil_to_timebase(scenario.end_ts),
        )
        scenario_requests.append(
            request.model_copy(
                update={
                    "request_timestamp": floor_to_timebase(request_ts),
                    "latest_finish_ts": max(latest_finish_ts, floor_to_timebase(request_ts) + timedelta(minutes=TIME_STEP_MINUTES)),
                    "metadata": metadata,
                }
            )
        )
    return scenario_requests


__all__ = ["RLScenarioSampler", "generate_requests_for_scenario"]
