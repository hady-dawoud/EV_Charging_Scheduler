from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError(f'Invalid boolean value: {value}')


@dataclass(frozen=True)
class PricingConfig:
    pricing_model: str = 'dundee_tariff_dynamic'
    dynamic_pricing_enabled: bool = True


def pricing_config_from_env() -> PricingConfig:
    return PricingConfig(
        pricing_model=os.getenv('PRICING_MODEL', 'dundee_tariff_dynamic'),
        dynamic_pricing_enabled=_bool_from_env(os.getenv('DYNAMIC_PRICING_ENABLED'), True),
    )
