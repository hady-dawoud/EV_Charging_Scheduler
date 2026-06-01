from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError(f'Invalid boolean value: {value}')


def _path_from_env(value: str | None) -> Path | None:
    if value is None or not value.strip():
        return None
    return Path(value).expanduser()


@dataclass(frozen=True)
class RoutingConfig:
    provider_name: str = 'simple_distance'
    osmnx_graph_path: Path | None = None
    osmnx_fail_closed: bool = False
    speed_kph: float = 30.0


def routing_config_from_env() -> RoutingConfig:
    graph = _path_from_env(os.getenv('OSMNX_GRAPH_PATH'))
    return RoutingConfig(
        provider_name=os.getenv('ROUTING_PROVIDER_NAME', 'simple_distance'),
        osmnx_graph_path=graph,
        osmnx_fail_closed=_bool_from_env(os.getenv('OSMNX_FAIL_CLOSED'), False),
    )
