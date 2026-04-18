"""Forecast-provider interfaces for the standalone Dundee simulator runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class ForecastRequest:
    """A sequence of timestamps sampled on the 15-minute internal time base."""

    series_name: str
    timestamps: tuple[datetime, ...] = field(default_factory=tuple)
    default_value: float = 0.0


@dataclass(frozen=True)
class ForecastSeries:
    """Simple forecast payload returned by simulator-ready forecast providers."""

    series_name: str
    timestamps: tuple[datetime, ...]
    values: tuple[float, ...]
    unit: str = "unknown"


class ForecastProvider(Protocol):
    """Protocol for price, load, and optional PV forecasts."""

    def forecast_background_load(self, request: ForecastRequest) -> ForecastSeries:
        """Return a background-load forecast over 15-minute intervals."""

    def forecast_price(self, request: ForecastRequest) -> ForecastSeries:
        """Return an energy-price forecast over 15-minute intervals."""

    def forecast_pv_generation(self, request: ForecastRequest) -> ForecastSeries:
        """Return an optional PV forecast over 15-minute intervals."""


class NullForecastProvider:
    """Safe provider that returns zeros on the simulator time base."""

    def __init__(self, default_value: float = 0.0) -> None:
        self.default_value = default_value

    def forecast_background_load(self, request: ForecastRequest) -> ForecastSeries:
        return self._constant_series(request, unit="kW")

    def forecast_price(self, request: ForecastRequest) -> ForecastSeries:
        return self._constant_series(request, unit="GBP_per_kWh")

    def forecast_pv_generation(self, request: ForecastRequest) -> ForecastSeries:
        return self._constant_series(request, unit="kW")

    def _constant_series(self, request: ForecastRequest, unit: str) -> ForecastSeries:
        values = tuple(request.default_value if request.default_value != 0.0 else self.default_value for _ in request.timestamps)
        return ForecastSeries(
            series_name=request.series_name,
            timestamps=request.timestamps,
            values=values,
            unit=unit,
        )


class PlaceholderForecastProvider:
    """Table-backed provider for Dundee replay and demo forecasts."""

    def __init__(
        self,
        background_load: pd.DataFrame | None = None,
        price_table: pd.DataFrame | None = None,
        pv_profile: pd.DataFrame | None = None,
    ) -> None:
        self.background_lookup = self._build_lookup(background_load, key_column="transformer_id", value_column="background_load_kw")
        self.price_lookup = self._build_lookup(price_table, key_column=None, value_column="price_gbp_per_kwh")
        self.pv_lookup = self._build_lookup(pv_profile, key_column=None, value_column="pv_generation_kw_per_mw")

    def forecast_background_load(self, request: ForecastRequest) -> ForecastSeries:
        return self._from_lookup(request, self.background_lookup, unit="kW")

    def forecast_price(self, request: ForecastRequest) -> ForecastSeries:
        return self._from_lookup(request, self.price_lookup, unit="GBP_per_kWh")

    def forecast_pv_generation(self, request: ForecastRequest) -> ForecastSeries:
        return self._from_lookup(request, self.pv_lookup, unit="kW_per_MW")

    def _from_lookup(
        self,
        request: ForecastRequest,
        lookup: dict[tuple[str, datetime], float] | dict[datetime, float],
        unit: str,
    ) -> ForecastSeries:
        values: list[float] = []
        for timestamp in request.timestamps:
            if isinstance(next(iter(lookup.keys()), None), tuple):
                values.append(float(lookup.get((request.series_name, timestamp), request.default_value)))
            else:
                values.append(float(lookup.get(timestamp, request.default_value)))
        return ForecastSeries(
            series_name=request.series_name,
            timestamps=request.timestamps,
            values=tuple(values),
            unit=unit,
        )

    @staticmethod
    def _build_lookup(
        frame: pd.DataFrame | None,
        key_column: str | None,
        value_column: str,
    ) -> dict[tuple[str, datetime], float] | dict[datetime, float]:
        if frame is None or frame.empty:
            return {}
        working = frame.copy()
        working["timestamp"] = pd.to_datetime(working["timestamp"])
        if key_column is None:
            return {timestamp.to_pydatetime(): float(value) for timestamp, value in zip(working["timestamp"], working[value_column])}
        return {
            (str(key), timestamp.to_pydatetime()): float(value)
            for key, timestamp, value in zip(working[key_column], working["timestamp"], working[value_column])
        }
