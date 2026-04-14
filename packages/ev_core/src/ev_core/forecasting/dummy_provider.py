"""Dummy forecast provider returning deterministic placeholder values."""

from __future__ import annotations

from .provider import ForecastProvider, ForecastRequest, ForecastSeries


class DummyForecastProvider(ForecastProvider):
    """Safe provider for local scaffolding and interface validation only."""

    def __init__(self, default_value: float = 0.0) -> None:
        self.default_value = default_value

    def forecast_background_load(self, request: ForecastRequest) -> ForecastSeries:
        return self._build_placeholder_series(request, unit="kW")

    def forecast_price(self, request: ForecastRequest) -> ForecastSeries:
        return self._build_placeholder_series(request, unit="currency_per_kWh")

    def forecast_pv_generation(self, request: ForecastRequest) -> ForecastSeries:
        return self._build_placeholder_series(request, unit="kW")

    def _build_placeholder_series(
        self,
        request: ForecastRequest,
        unit: str,
    ) -> ForecastSeries:
        values = tuple(self.default_value for _ in request.timestamps)
        return ForecastSeries(
            series_name=request.series_name,
            timestamps=request.timestamps,
            values=values,
            unit=unit,
        )
