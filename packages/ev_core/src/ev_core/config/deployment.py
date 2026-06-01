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
class RLDeploymentConfig:
    policy_name: str = 'rl_maskable_ppo'
    checkpoint_path: Path | None = None
    fallback_policy_name: str = 'weighted_score'
    fail_closed: bool = False


def rl_deployment_config_from_env() -> RLDeploymentConfig:
    return RLDeploymentConfig(
        checkpoint_path=_path_from_env(os.getenv('RL_POLICY_CHECKPOINT_PATH')),
        fallback_policy_name=os.getenv('RL_FALLBACK_POLICY_NAME', 'weighted_score'),
        fail_closed=_bool_from_env(os.getenv('RL_POLICY_FAIL_CLOSED'), False),
    )
