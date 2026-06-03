from __future__ import annotations

import os
from dataclasses import dataclass


def bool_from_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError(f'Invalid boolean value: {value}')


@dataclass(frozen=True)
class DigitalTwinRuntimeConfig:
    replay_day: str | None = None
    start_hour: int = 12
    start_minute: int = 0
    warm_start_hours: int = 0
    continuous_live_enabled: bool = False
    live_request_generation_enabled: bool = False
    live_demand_level: str = 'normal'
    live_request_rate_multiplier: float = 1.0
    max_generated_requests_per_tick: int = 3


def runtime_config_from_env() -> DigitalTwinRuntimeConfig:
    return DigitalTwinRuntimeConfig(
        continuous_live_enabled=bool_from_env(os.getenv('CONTINUOUS_LIVE_ENABLED'), False),
        live_request_generation_enabled=bool_from_env(os.getenv('LIVE_REQUEST_GENERATION_ENABLED'), False),
        live_demand_level=os.getenv('LIVE_DEMAND_LEVEL', 'normal'),
        live_request_rate_multiplier=float(os.getenv('LIVE_REQUEST_RATE_MULTIPLIER', '1.0')),
        max_generated_requests_per_tick=int(os.getenv('MAX_GENERATED_REQUESTS_PER_TICK', '3')),
    )
