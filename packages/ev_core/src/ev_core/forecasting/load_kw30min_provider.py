"""Lazy smoke provider for the load_kw_30min forecasting artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from ev_core.config.forecasting import ForecastingConfig


MODEL_FILENAME = "lstm_huber_load_kw_30min.keras"
FEATURE_SCALER_FILENAME = "load_kw_30min_feature_scaler.joblib"
TARGET_SCALER_FILENAME = "load_kw_30min_target_scaler.joblib"
METADATA_FILENAME = "load_kw_30min_training_metadata.json"
EXPECTED_TARGET = "load_kw_30min"
EXPECTED_FREQUENCY = "30min"
EXPECTED_LOOKBACK = 48
EXPECTED_FEATURE_COUNT = 148


class ForecastProviderError(RuntimeError):
    """Raised when fail-closed forecast diagnostics cannot be produced."""


@dataclass(frozen=True)
class ForecastDiagnosticResult:
    provider: str
    status: str
    model_dir: str
    target: str | None = None
    frequency: str | None = None
    lookback: int | None = None
    feature_count: int | None = None
    horizon_steps: int | None = None
    value: float | None = None
    unit: str = "kW"
    timestamp: datetime | None = None
    feature_assembly: str = "unavailable"
    is_production: bool = False
    used_for_ranking: bool = False
    ranking_mode: str = "metadata_only"
    error: str | None = None
    input_shape: list[int] | None = None

    def metadata(self) -> dict[str, Any]:
        payload = {
            "forecast_provider": self.provider,
            "forecast_status": self.status,
            "forecast_model_dir": self.model_dir,
            "forecast_target": self.target,
            "forecast_frequency": self.frequency,
            "forecast_lookback": self.lookback,
            "forecast_feature_count": self.feature_count,
            "forecast_horizon_steps": self.horizon_steps,
            "forecast_value": self.value,
            "forecast_unit": self.unit,
            "forecast_timestamp": None if self.timestamp is None else self.timestamp.isoformat(),
            "forecast_feature_assembly": self.feature_assembly,
            "forecast_is_production": self.is_production,
            "forecast_used_for_ranking": self.used_for_ranking,
            "forecast_ranking_mode": self.ranking_mode,
            "forecast_error": self.error,
            "forecast_input_shape": self.input_shape,
        }
        return {key: value for key, value in payload.items() if value is not None}


class DisabledForecastDiagnosticsProvider:
    provider_name = "disabled"

    def __init__(self, *, model_dir: str | Path, ranking_mode: str = "metadata_only") -> None:
        self.model_dir = Path(model_dir)
        self.ranking_mode = ranking_mode

    def smoke_forecast(self, timestamp: datetime | None = None, *, allow_smoke_template: bool = False) -> ForecastDiagnosticResult:
        return ForecastDiagnosticResult(
            provider=self.provider_name,
            status="disabled",
            model_dir=str(self.model_dir),
            timestamp=timestamp,
            feature_assembly="disabled",
            ranking_mode=self.ranking_mode,
        )


class KerasLoadKw30minForecastProvider:
    provider_name = "keras_load_kw_30min"

    def __init__(
        self,
        *,
        model_dir: str | Path,
        ranking_mode: str = "metadata_only",
        fail_closed: bool = False,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.ranking_mode = ranking_mode
        self.fail_closed = bool(fail_closed)
        self._metadata: dict[str, Any] | None = None

    def smoke_forecast(self, timestamp: datetime | None = None, *, allow_smoke_template: bool = False) -> ForecastDiagnosticResult:
        try:
            self._validate_artifacts()
            metadata = self._load_metadata()
            self._validate_metadata(metadata)
            self._load_optional_dependencies()
            if not allow_smoke_template:
                raise ForecastProviderError("Full 148-feature assembly is not implemented for production forecasting.")
            value = self._smoke_template_value(metadata)
            return self._result(
                status="smoke_template",
                timestamp=timestamp,
                metadata=metadata,
                value=value,
                feature_assembly="smoke_template",
                is_production=False,
            )
        except Exception as exc:
            if self.fail_closed:
                if isinstance(exc, ForecastProviderError):
                    raise
                raise ForecastProviderError(str(exc)) from exc
            status = _status_for_error(exc)
            metadata = self._metadata or {}
            return self._result(
                status=status,
                timestamp=timestamp,
                metadata=metadata,
                error=str(exc),
                feature_assembly="unavailable",
                is_production=False,
            )

    def _validate_artifacts(self) -> None:
        missing = [
            path
            for path in (
                self.model_dir / MODEL_FILENAME,
                self.model_dir / FEATURE_SCALER_FILENAME,
                self.model_dir / TARGET_SCALER_FILENAME,
                self.model_dir / METADATA_FILENAME,
            )
            if not path.exists()
        ]
        if missing:
            raise FileNotFoundError("Missing forecast artifacts: " + ", ".join(str(path) for path in missing))

    def _load_metadata(self) -> dict[str, Any]:
        path = self.model_dir / METADATA_FILENAME
        self._metadata = json.loads(path.read_text(encoding="utf-8"))
        return self._metadata

    def _validate_metadata(self, metadata: dict[str, Any]) -> None:
        problems: list[str] = []
        if metadata.get("target") != EXPECTED_TARGET:
            problems.append(f"target={metadata.get('target')!r}")
        if metadata.get("frequency") != EXPECTED_FREQUENCY:
            problems.append(f"frequency={metadata.get('frequency')!r}")
        if int(metadata.get("lookback") or 0) != EXPECTED_LOOKBACK:
            problems.append(f"lookback={metadata.get('lookback')!r}")
        if int(metadata.get("feature_count") or 0) != EXPECTED_FEATURE_COUNT:
            problems.append(f"feature_count={metadata.get('feature_count')!r}")
        input_shape = metadata.get("input_shape")
        if input_shape and list(input_shape) != [EXPECTED_LOOKBACK, EXPECTED_FEATURE_COUNT]:
            problems.append(f"input_shape={input_shape!r}")
        if problems:
            raise ValueError("Invalid load_kw_30min metadata: " + ", ".join(problems))

    def _load_optional_dependencies(self) -> tuple[Any, Any]:
        import joblib
        from tensorflow import keras

        feature_scaler = joblib.load(self.model_dir / FEATURE_SCALER_FILENAME)
        target_scaler = joblib.load(self.model_dir / TARGET_SCALER_FILENAME)
        model = keras.models.load_model(self.model_dir / MODEL_FILENAME)
        self._validate_model_shape(model)
        return (feature_scaler, target_scaler)

    def _validate_model_shape(self, model: Any) -> None:
        input_shape = getattr(model, "input_shape", None)
        if not input_shape:
            return
        shape = list(input_shape)
        trailing = shape[-2:] if len(shape) >= 2 else shape
        if trailing != [EXPECTED_LOOKBACK, EXPECTED_FEATURE_COUNT]:
            raise ValueError(f"Model input shape {input_shape!r} is not compatible with [48, 148].")

    def _smoke_template_value(self, metadata: dict[str, Any]) -> float:
        _template = np.zeros((1, int(metadata["lookback"]), int(metadata["feature_count"])), dtype=np.float32)
        return 0.0

    def _result(
        self,
        *,
        status: str,
        timestamp: datetime | None,
        metadata: dict[str, Any],
        value: float | None = None,
        error: str | None = None,
        feature_assembly: str,
        is_production: bool,
    ) -> ForecastDiagnosticResult:
        return ForecastDiagnosticResult(
            provider=self.provider_name,
            status=status,
            model_dir=str(self.model_dir),
            target=metadata.get("target"),
            frequency=metadata.get("frequency"),
            lookback=_optional_int(metadata.get("lookback")),
            feature_count=_optional_int(metadata.get("feature_count")),
            horizon_steps=_optional_int(metadata.get("horizon")),
            value=value,
            timestamp=timestamp,
            feature_assembly=feature_assembly,
            is_production=is_production,
            used_for_ranking=False,
            ranking_mode=self.ranking_mode,
            error=error,
            input_shape=list(metadata.get("input_shape") or []) or None,
        )


def build_forecast_diagnostics_provider(config: ForecastingConfig):
    if config.provider_name in {"", "disabled", "none"}:
        return DisabledForecastDiagnosticsProvider(model_dir=config.model_dir, ranking_mode=config.ranking_mode)
    if config.provider_name == "keras_load_kw_30min":
        return KerasLoadKw30minForecastProvider(
            model_dir=config.model_dir,
            ranking_mode=config.ranking_mode,
            fail_closed=config.fail_closed,
        )
    if config.fail_closed:
        raise ForecastProviderError(f"Unsupported forecast provider: {config.provider_name}")
    return DisabledForecastDiagnosticsProvider(model_dir=config.model_dir, ranking_mode=config.ranking_mode)


def _status_for_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "artifact_missing"
    if isinstance(exc, ImportError):
        return "dependency_missing"
    if isinstance(exc, ValueError):
        return "metadata_invalid"
    return "forecast_unavailable"


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "DisabledForecastDiagnosticsProvider",
    "ForecastDiagnosticResult",
    "ForecastProviderError",
    "KerasLoadKw30minForecastProvider",
    "build_forecast_diagnostics_provider",
]
