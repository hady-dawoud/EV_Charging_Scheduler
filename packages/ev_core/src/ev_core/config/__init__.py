from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .deployment import RLDeploymentConfig, rl_deployment_config_from_env
from .paths import ProjectPathsConfig, default_project_paths
from .pricing import PricingConfig, pricing_config_from_env
from .recommendation import RecommendationConfig, recommendation_config_from_env
from .routing import RoutingConfig, routing_config_from_env
from .runtime import DigitalTwinRuntimeConfig, runtime_config_from_env
from .topology import TopologyConfig, topology_config_from_env
from .training import ForecastTrainingConfig, RLTrainingConfig, rl_training_config_from_env


@dataclass(frozen=True)
class EVSmartChargingConfig:
    paths: ProjectPathsConfig
    runtime: DigitalTwinRuntimeConfig
    recommendation: RecommendationConfig
    routing: RoutingConfig
    pricing: PricingConfig
    topology: TopologyConfig
    rl_training: RLTrainingConfig
    forecast_training: ForecastTrainingConfig
    rl_deployment: RLDeploymentConfig


def bool_from_env(value: str | None, default: bool = False) -> bool:
    from .runtime import bool_from_env as _bool_from_env

    return _bool_from_env(value, default)


def path_from_env(value: str | None) -> Path | None:
    if value is None or not value.strip():
        return None
    return Path(value).expanduser()


def default_config(repo_root: Path | str | None = None) -> EVSmartChargingConfig:
    return EVSmartChargingConfig(
        paths=default_project_paths(repo_root=repo_root),
        runtime=DigitalTwinRuntimeConfig(),
        recommendation=RecommendationConfig(),
        routing=RoutingConfig(),
        pricing=PricingConfig(),
        topology=TopologyConfig(),
        rl_training=RLTrainingConfig(),
        forecast_training=ForecastTrainingConfig(),
        rl_deployment=RLDeploymentConfig(),
    )


def config_from_env(repo_root: Path | str | None = None) -> EVSmartChargingConfig:
    return EVSmartChargingConfig(
        paths=default_project_paths(repo_root=repo_root),
        runtime=runtime_config_from_env(),
        recommendation=recommendation_config_from_env(),
        routing=routing_config_from_env(),
        pricing=pricing_config_from_env(),
        topology=topology_config_from_env(),
        rl_training=rl_training_config_from_env(),
        forecast_training=ForecastTrainingConfig(),
        rl_deployment=rl_deployment_config_from_env(),
    )


__all__ = [
    'DigitalTwinRuntimeConfig',
    'EVSmartChargingConfig',
    'ForecastTrainingConfig',
    'PricingConfig',
    'ProjectPathsConfig',
    'RLDeploymentConfig',
    'RLTrainingConfig',
    'RecommendationConfig',
    'RoutingConfig',
    'TopologyConfig',
    'bool_from_env',
    'config_from_env',
    'default_config',
    'default_project_paths',
    'path_from_env',
]
