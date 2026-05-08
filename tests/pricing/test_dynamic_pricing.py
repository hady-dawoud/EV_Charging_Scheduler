from __future__ import annotations

import pytest

from ev_core.pricing.dynamic_pricing import (
    DynamicPricingInput,
    calculate_dynamic_price,
)


def test_low_load_and_high_headroom_applies_discount_multiplier() -> None:
    result = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=0.30,
            transformer_capacity_kw=100.0,
            transformer_net_load_kw=30.0,
            transformer_headroom_kw=70.0,
        )
    )

    assert result.transformer_multiplier == 0.90
    assert result.congestion_multiplier == 1.0
    assert round(result.dynamic_price_per_kwh, 3) == 0.27
    assert result.reason == "high_transformer_headroom"


def test_normal_load_keeps_transformer_multiplier_neutral() -> None:
    result = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=0.30,
            transformer_capacity_kw=100.0,
            transformer_net_load_kw=60.0,
            transformer_headroom_kw=40.0,
        )
    )

    assert result.transformer_multiplier == 1.0
    assert round(result.dynamic_price_per_kwh, 3) == 0.30
    assert result.reason == "normal_transformer_load"


@pytest.mark.parametrize(
    ("net_load_kw", "headroom_kw", "expected_multiplier", "expected_reason"),
    [
        (75.0, 25.0, 1.30, "high_transformer_load"),
        (90.0, 10.0, 1.60, "very_high_transformer_load"),
        (100.0, 0.0, 2.00, "transformer_overloaded"),
    ],
)
def test_high_load_bands_apply_expected_transformer_multiplier(
    net_load_kw: float,
    headroom_kw: float,
    expected_multiplier: float,
    expected_reason: str,
) -> None:
    result = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=0.30,
            transformer_capacity_kw=100.0,
            transformer_net_load_kw=net_load_kw,
            transformer_headroom_kw=headroom_kw,
        )
    )

    assert result.transformer_multiplier == expected_multiplier
    assert result.reason == expected_reason


def test_station_queue_and_utilization_increase_congestion_multiplier() -> None:
    result = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=0.30,
            transformer_capacity_kw=100.0,
            transformer_net_load_kw=60.0,
            transformer_headroom_kw=40.0,
            station_queue_length=3,
            station_utilization=0.80,
        )
    )

    assert result.transformer_multiplier == 1.0
    assert round(result.congestion_multiplier, 2) == 1.27
    assert round(result.dynamic_price_per_kwh, 3) == 0.381


def test_dynamic_price_is_clamped_to_upper_bound() -> None:
    result = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=0.10,
            transformer_capacity_kw=100.0,
            transformer_net_load_kw=100.0,
            transformer_headroom_kw=0.0,
            station_queue_length=10,
            station_utilization=1.0,
        )
    )

    assert round(result.congestion_multiplier, 2) == 1.40
    assert round(result.dynamic_price_per_kwh, 2) == 0.28


def test_invalid_capacity_is_handled_safely() -> None:
    result = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=0.20,
            transformer_capacity_kw=0.0,
            transformer_net_load_kw=80.0,
            transformer_headroom_kw=-80.0,
        )
    )

    assert result.load_ratio == 0.0
    assert result.headroom_ratio == 0.0
    assert result.transformer_multiplier == 1.0
    assert round(result.dynamic_price_per_kwh, 2) == 0.20
