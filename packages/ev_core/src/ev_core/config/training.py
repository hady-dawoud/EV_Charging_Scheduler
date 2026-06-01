from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _path_from_env(value: str | None) -> Path | None:
    if value is None or not value.strip():
        return None
    return Path(value).expanduser()


@dataclass(frozen=True)
class RLTrainingConfig:
    split: str = 'train'
    seed: int = 1000
    duration_hours: int = 1
    demand_level: str = 'normal'
    routing_provider_name: str = 'simple_distance'
    dynamic_pricing_enabled: bool = True
    checkpoint_dir: Path | None = None
    evaluation_dir: Path | None = None
    tensorboard_dir: Path | None = None
    figures_dir: Path | None = None


@dataclass(frozen=True)
class ForecastTrainingConfig:
    horizon_hours: int = 1
    target_level: str = 'zone'
    forecast_profile: str = 'none'


def rl_training_config_from_env() -> RLTrainingConfig:
    return RLTrainingConfig(
        checkpoint_dir=_path_from_env(os.getenv('RL_CHECKPOINT_DIR')),
        evaluation_dir=_path_from_env(os.getenv('RL_EVALUATION_DIR')),
        tensorboard_dir=_path_from_env(os.getenv('RL_TENSORBOARD_DIR')),
        figures_dir=_path_from_env(os.getenv('RL_FIGURES_DIR')),
    )
