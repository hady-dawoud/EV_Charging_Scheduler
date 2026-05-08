"""Simplified Dundee charger-class tariffs for simulator recommendations."""

from __future__ import annotations

from typing import Any


DUNDEE_TARIFF_PRICES_GBP_PER_KWH = {
    "ac_standard": 0.50,
    "ac_fast": 0.57,
    "rapid": 0.69,
    "ultra_rapid": 0.75,
    "unknown": 0.57,
}


def _normalize_connector_type(connector_type: str | None) -> str:
    return str(connector_type or "").strip().lower().replace("-", "_").replace(" ", "_")


def classify_dundee_tariff_class(
    *,
    connector_type: str | None,
    power_kw: float | None,
) -> str:
    """Classify a charger into one of the simplified Dundee tariff buckets."""

    normalized = _normalize_connector_type(connector_type)
    power = None if power_kw is None else max(float(power_kw), 0.0)

    if "ultra" in normalized:
        return "ultra_rapid"
    if "rapid" in normalized and power is not None and power >= 100.0:
        return "ultra_rapid"
    if "rapid" in normalized or normalized == "dc" or "dc" in normalized:
        if power is not None and power >= 100.0:
            return "ultra_rapid"
        if power is None or power >= 50.0:
            return "rapid"
    if normalized == "ac" or "ac" in normalized:
        if power is not None and power >= 43.0:
            return "rapid"
        if power is not None and power > 7.0:
            return "ac_fast"
        return "ac_standard"
    if power is not None:
        if power <= 7.0:
            return "ac_standard"
        if power <= 22.0:
            return "ac_fast"
        if power >= 100.0:
            return "ultra_rapid"
        if power >= 50.0:
            return "rapid"
    return "unknown"


def dundee_base_price_per_kwh(
    *,
    connector_type: str | None,
    power_kw: float | None,
) -> float:
    """Return the simplified Dundee base tariff for the supplied charger characteristics."""

    tariff_class = classify_dundee_tariff_class(connector_type=connector_type, power_kw=power_kw)
    return float(DUNDEE_TARIFF_PRICES_GBP_PER_KWH[tariff_class])


def build_dundee_tariff_metadata(
    *,
    connector_type: str | None,
    power_kw: float | None,
) -> dict[str, Any]:
    """Return tariff classification plus fallback transparency metadata."""

    tariff_class = classify_dundee_tariff_class(connector_type=connector_type, power_kw=power_kw)
    return {
        "tariff_class": tariff_class,
        "base_price_per_kwh": dundee_base_price_per_kwh(connector_type=connector_type, power_kw=power_kw),
        "tariff_fallback_used": tariff_class == "unknown",
        "selected_connector_type": connector_type,
        "selected_connector_power_kw": None if power_kw is None else float(power_kw),
    }


__all__ = [
    "DUNDEE_TARIFF_PRICES_GBP_PER_KWH",
    "build_dundee_tariff_metadata",
    "classify_dundee_tariff_class",
    "dundee_base_price_per_kwh",
]
