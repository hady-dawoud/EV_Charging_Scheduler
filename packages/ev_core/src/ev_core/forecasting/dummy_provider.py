"""Backward-compatible dummy providers for Dundee simulator development."""

from __future__ import annotations

from .provider import ForecastRequest, ForecastSeries, NullForecastProvider, PlaceholderForecastProvider


class DummyForecastProvider(NullForecastProvider):
    """Compatibility wrapper that behaves like the null forecast provider."""

    pass


__all__ = [
    "DummyForecastProvider",
    "ForecastRequest",
    "ForecastSeries",
    "NullForecastProvider",
    "PlaceholderForecastProvider",
]
