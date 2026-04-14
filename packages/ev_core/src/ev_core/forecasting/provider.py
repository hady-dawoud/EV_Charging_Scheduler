"""Forecast-provider interfaces used by future simulation and ranking flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ForecastRequest:
    """A sequence of timestamps sampled on the 15-minute internal time base."""

    series_name: str
    timestamps: tuple[datetime, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ForecastSeries:
    """Simple forecast payload returned by placeholder providers."""

    series_name: str
    timestamps: tuple[datetime, ...]
    values: tuple[float, ...]
    unit: str = "unknown"


class ForecastProvider(Protocol):
    """Protocol for price, load, and optional PV forecast providers."""

    def forecast_background_load(self, request: ForecastRequest) -> ForecastSeries:
        """Return a background-load forecast over 15-minute intervals."""

    def forecast_price(self, request: ForecastRequest) -> ForecastSeries:
        """Return an energy-price forecast over 15-minute intervals."""

    def forecast_pv_generation(self, request: ForecastRequest) -> ForecastSeries:
        """Return an optional PV forecast over 15-minute intervals."""
