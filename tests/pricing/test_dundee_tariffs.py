from __future__ import annotations

from ev_core.pricing.dundee_tariffs import (
    classify_dundee_tariff_class,
    dundee_base_price_per_kwh,
)


def test_ac_standard_7kw_uses_expected_base_tariff() -> None:
    assert classify_dundee_tariff_class(connector_type="AC", power_kw=7.0) == "ac_standard"
    assert dundee_base_price_per_kwh(connector_type="AC", power_kw=7.0) == 0.50


def test_ac_fast_22kw_uses_expected_base_tariff() -> None:
    assert classify_dundee_tariff_class(connector_type="AC", power_kw=22.0) == "ac_fast"
    assert dundee_base_price_per_kwh(connector_type="AC", power_kw=22.0) == 0.57


def test_rapid_50kw_uses_expected_base_tariff() -> None:
    assert classify_dundee_tariff_class(connector_type="Rapid", power_kw=50.0) == "rapid"
    assert dundee_base_price_per_kwh(connector_type="Rapid", power_kw=50.0) == 0.69


def test_ultra_rapid_100kw_uses_expected_base_tariff() -> None:
    assert classify_dundee_tariff_class(connector_type="Rapid", power_kw=100.0) == "ultra_rapid"
    assert dundee_base_price_per_kwh(connector_type="Rapid", power_kw=100.0) == 0.75


def test_same_dynamic_conditions_preserve_tariff_ordering() -> None:
    prices = [
        dundee_base_price_per_kwh(connector_type="AC", power_kw=7.0),
        dundee_base_price_per_kwh(connector_type="AC", power_kw=22.0),
        dundee_base_price_per_kwh(connector_type="Rapid", power_kw=50.0),
        dundee_base_price_per_kwh(connector_type="Ultra Rapid", power_kw=150.0),
    ]

    assert prices == sorted(prices)
