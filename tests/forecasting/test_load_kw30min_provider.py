from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from ev_core.config.forecasting import ForecastingConfig, forecasting_config_from_env
from ev_core.forecasting.load_kw30min_provider import (
    ForecastProviderError,
    KerasLoadKw30minForecastProvider,
    build_forecast_diagnostics_provider,
)


def write_metadata(path: Path, *, target: str = "load_kw_30min", lookback: int = 48, feature_count: int = 148) -> None:
    path.write_text(
        json.dumps(
            {
                "target": target,
                "frequency": "30min",
                "horizon": 1,
                "lookback": lookback,
                "feature_count": feature_count,
                "input_shape": [lookback, feature_count],
                "target_shape": [1],
            }
        ),
        encoding="utf-8",
    )


def write_artifacts(model_dir: Path) -> None:
    model_dir.mkdir(exist_ok=True)
    (model_dir / "lstm_huber_load_kw_30min.keras").write_text("model", encoding="utf-8")
    (model_dir / "load_kw_30min_feature_scaler.joblib").write_text("feature", encoding="utf-8")
    (model_dir / "load_kw_30min_target_scaler.joblib").write_text("target", encoding="utf-8")
    write_metadata(model_dir / "load_kw_30min_training_metadata.json")


def test_forecasting_config_defaults_to_disabled(monkeypatch) -> None:
    monkeypatch.delenv("FORECAST_PROVIDER", raising=False)
    monkeypatch.delenv("FORECAST_MODEL_DIR", raising=False)
    monkeypatch.delenv("FORECAST_RANKING_MODE", raising=False)
    monkeypatch.delenv("FORECAST_FAIL_CLOSED", raising=False)

    config = forecasting_config_from_env()

    assert config.provider_name == "disabled"
    assert config.model_dir == Path("models/forecasting/load_kw_30min")
    assert config.ranking_mode == "metadata_only"
    assert config.fail_closed is False


def test_disabled_provider_returns_noop_metadata_without_loading_dependencies(tmp_path) -> None:
    provider = build_forecast_diagnostics_provider(ForecastingConfig(provider_name="disabled", model_dir=tmp_path))

    result = provider.smoke_forecast(datetime(2024, 6, 10, 12, 0))

    assert result.metadata()["forecast_provider"] == "disabled"
    assert result.metadata()["forecast_status"] == "disabled"
    assert result.metadata()["forecast_used_for_ranking"] is False


def test_provider_reports_missing_model_dir_as_controlled_diagnostic(tmp_path) -> None:
    provider = KerasLoadKw30minForecastProvider(model_dir=tmp_path / "missing", fail_closed=False)

    result = provider.smoke_forecast(datetime(2024, 6, 10, 12, 0), allow_smoke_template=True)

    assert result.status == "artifact_missing"
    assert "forecast_error" in result.metadata()


def test_provider_fail_closed_raises_for_missing_artifacts(tmp_path) -> None:
    provider = KerasLoadKw30minForecastProvider(model_dir=tmp_path / "missing", fail_closed=True)

    with pytest.raises(ForecastProviderError, match="Missing forecast artifacts"):
        provider.smoke_forecast(datetime(2024, 6, 10, 12, 0), allow_smoke_template=True)


def test_provider_validates_metadata_contract(tmp_path) -> None:
    write_artifacts(tmp_path)
    write_metadata(tmp_path / "load_kw_30min_training_metadata.json", target="other_target")
    provider = KerasLoadKw30minForecastProvider(model_dir=tmp_path, fail_closed=False)

    result = provider.smoke_forecast(datetime(2024, 6, 10, 12, 0), allow_smoke_template=True)

    assert result.status == "metadata_invalid"
    assert "target" in result.error


def test_provider_dependency_error_is_controlled_when_enabled(monkeypatch, tmp_path) -> None:
    write_artifacts(tmp_path)
    provider = KerasLoadKw30minForecastProvider(model_dir=tmp_path, fail_closed=False)
    monkeypatch.setattr(provider, "_load_optional_dependencies", lambda: (_ for _ in ()).throw(ImportError("tensorflow missing")))

    result = provider.smoke_forecast(datetime(2024, 6, 10, 12, 0), allow_smoke_template=True)

    assert result.status == "dependency_missing"
    assert result.is_production is False
    assert result.used_for_ranking is False
    assert "tensorflow missing" in result.error


def test_provider_smoke_template_is_labeled_non_production(monkeypatch, tmp_path) -> None:
    write_artifacts(tmp_path)
    provider = KerasLoadKw30minForecastProvider(model_dir=tmp_path, fail_closed=False)
    monkeypatch.setattr(provider, "_load_optional_dependencies", lambda: (None, object()))

    result = provider.smoke_forecast(datetime(2024, 6, 10, 12, 0), allow_smoke_template=True)

    metadata = result.metadata()
    assert result.status == "smoke_template"
    assert metadata["forecast_feature_assembly"] == "smoke_template"
    assert metadata["forecast_is_production"] is False
    assert metadata["forecast_used_for_ranking"] is False
    assert metadata["forecast_target"] == "load_kw_30min"
    assert metadata["forecast_lookback"] == 48
    assert metadata["forecast_feature_count"] == 148
