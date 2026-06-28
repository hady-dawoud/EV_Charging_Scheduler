from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .deployment import _bool_from_env


KNOWN_FORECAST_PROVIDERS = frozenset({"disabled", "keras_load_kw_30min"})
KNOWN_FORECAST_RANKING_MODES = frozenset({"metadata_only"})
DEFAULT_FORECAST_MODEL_DIR = Path("models/forecasting/load_kw_30min")


@dataclass(frozen=True)
class ForecastingConfig:
    provider_name: str = "disabled"
    model_dir: Path = DEFAULT_FORECAST_MODEL_DIR
    ranking_mode: str = "metadata_only"
    fail_closed: bool = False


def forecasting_config_from_env() -> ForecastingConfig:
    provider_name = _normalized_env("FORECAST_PROVIDER", "disabled")
    ranking_mode = _normalized_env("FORECAST_RANKING_MODE", "metadata_only")
    return ForecastingConfig(
        provider_name=provider_name,
        model_dir=Path(os.getenv("FORECAST_MODEL_DIR", str(DEFAULT_FORECAST_MODEL_DIR))).expanduser(),
        ranking_mode=ranking_mode,
        fail_closed=_bool_from_env(os.getenv("FORECAST_FAIL_CLOSED"), False),
    )


def _normalized_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower()


__all__ = [
    "DEFAULT_FORECAST_MODEL_DIR",
    "ForecastingConfig",
    "KNOWN_FORECAST_PROVIDERS",
    "KNOWN_FORECAST_RANKING_MODES",
    "forecasting_config_from_env",
]
