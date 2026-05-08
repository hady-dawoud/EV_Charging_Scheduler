"""Dynamic pricing overlay for recommendation-time simulation costs.

This module adjusts the displayed recommendation price signal used by the
simulator. It is intentionally a lightweight, deterministic overlay on top of
the forecast/base tariff and does not represent a real billing or market tariff.
"""

from __future__ import annotations

from dataclasses import dataclass

OVERLOAD_MULTIPLIER = 2.00
VERY_HIGH_LOAD_MULTIPLIER = 1.60
HIGH_LOAD_MULTIPLIER = 1.30
HIGH_HEADROOM_DISCOUNT_MULTIPLIER = 0.90
NEUTRAL_MULTIPLIER = 1.00

OVERLOAD_LOAD_RATIO_THRESHOLD = 1.00
VERY_HIGH_LOAD_RATIO_THRESHOLD = 0.90
HIGH_LOAD_RATIO_THRESHOLD = 0.75
LOW_LOAD_RATIO_THRESHOLD = 0.35
HIGH_HEADROOM_RATIO_THRESHOLD = 0.50

QUEUE_MULTIPLIER_PER_VEHICLE = 0.05
MAX_QUEUE_MULTIPLIER = 0.25
UTILIZATION_MULTIPLIER_FACTOR = 0.15
MAX_UTILIZATION_MULTIPLIER = 0.15

MIN_PRICE_FACTOR = 0.75
MAX_PRICE_FACTOR = 3.0
ABSOLUTE_MIN_PRICE_PER_KWH = 0.05


@dataclass(frozen=True)
class DynamicPricingInput:
    base_price_per_kwh: float
    transformer_capacity_kw: float
    transformer_net_load_kw: float
    transformer_headroom_kw: float
    station_queue_length: int = 0
    station_utilization: float = 0.0


@dataclass(frozen=True)
class DynamicPricingResult:
    base_price_per_kwh: float
    dynamic_price_per_kwh: float
    transformer_multiplier: float
    congestion_multiplier: float
    load_ratio: float
    headroom_ratio: float
    reason: str


def calculate_dynamic_price(input_: DynamicPricingInput) -> DynamicPricingResult:
    """Return a simulation/display price overlay for recommendation ranking.

    The returned dynamic price keeps the base tariff as the primary signal and
    layers on a grid/congestion adjustment suitable for simulator-facing cost
    estimation and transparency. It must not be interpreted as customer billing.
    """

    base_price = max(float(input_.base_price_per_kwh), 0.0)
    capacity_kw = float(input_.transformer_capacity_kw)
    if capacity_kw > 0.0:
        load_ratio = max(float(input_.transformer_net_load_kw), 0.0) / capacity_kw
        headroom_ratio = max(float(input_.transformer_headroom_kw), 0.0) / capacity_kw
    else:
        load_ratio = 0.0
        headroom_ratio = 0.0

    transformer_multiplier = NEUTRAL_MULTIPLIER
    reason = "normal_transformer_load"
    if capacity_kw > 0.0:
        if load_ratio >= OVERLOAD_LOAD_RATIO_THRESHOLD:
            transformer_multiplier = OVERLOAD_MULTIPLIER
            reason = "transformer_overloaded"
        elif load_ratio >= VERY_HIGH_LOAD_RATIO_THRESHOLD:
            transformer_multiplier = VERY_HIGH_LOAD_MULTIPLIER
            reason = "very_high_transformer_load"
        elif load_ratio >= HIGH_LOAD_RATIO_THRESHOLD:
            transformer_multiplier = HIGH_LOAD_MULTIPLIER
            reason = "high_transformer_load"
        elif load_ratio <= LOW_LOAD_RATIO_THRESHOLD and headroom_ratio >= HIGH_HEADROOM_RATIO_THRESHOLD:
            transformer_multiplier = HIGH_HEADROOM_DISCOUNT_MULTIPLIER
            reason = "high_transformer_headroom"

    queue_component = min(max(int(input_.station_queue_length), 0) * QUEUE_MULTIPLIER_PER_VEHICLE, MAX_QUEUE_MULTIPLIER)
    utilization_component = min(max(float(input_.station_utilization), 0.0) * UTILIZATION_MULTIPLIER_FACTOR, MAX_UTILIZATION_MULTIPLIER)
    congestion_multiplier = 1.0 + queue_component + utilization_component

    dynamic_price = base_price * transformer_multiplier * congestion_multiplier
    min_price_per_kwh = max(base_price * MIN_PRICE_FACTOR, ABSOLUTE_MIN_PRICE_PER_KWH)
    max_price_per_kwh = max(base_price * MAX_PRICE_FACTOR, min_price_per_kwh)
    dynamic_price = _clamp(dynamic_price, min_price_per_kwh, max_price_per_kwh)

    return DynamicPricingResult(
        base_price_per_kwh=base_price,
        dynamic_price_per_kwh=dynamic_price,
        transformer_multiplier=transformer_multiplier,
        congestion_multiplier=congestion_multiplier,
        load_ratio=load_ratio,
        headroom_ratio=headroom_ratio,
        reason=reason,
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(float(value), float(minimum)), float(maximum))


__all__ = [
    "DynamicPricingInput",
    "DynamicPricingResult",
    "calculate_dynamic_price",
]
