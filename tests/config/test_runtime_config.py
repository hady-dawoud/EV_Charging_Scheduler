import pytest

from ev_core.config.runtime import DigitalTwinRuntimeConfig, bool_from_env, runtime_config_from_env


def test_runtime_config_defaults() -> None:
    cfg = DigitalTwinRuntimeConfig()
    assert cfg.start_hour == 12
    assert cfg.live_demand_level == 'normal'


def test_bool_from_env_parsing() -> None:
    assert bool_from_env('true') is True
    assert bool_from_env('0', default=True) is False
    assert bool_from_env(None, default=True) is True


def test_bool_from_env_invalid_raises() -> None:
    with pytest.raises(ValueError):
        bool_from_env('maybe')


def test_runtime_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CONTINUOUS_LIVE_ENABLED', 'true')
    monkeypatch.setenv('LIVE_REQUEST_GENERATION_ENABLED', '1')
    monkeypatch.setenv('LIVE_DEMAND_LEVEL', 'busy')
    monkeypatch.setenv('LIVE_REQUEST_RATE_MULTIPLIER', '1.7')
    monkeypatch.setenv('MAX_GENERATED_REQUESTS_PER_TICK', '5')
    cfg = runtime_config_from_env()
    assert cfg.continuous_live_enabled is True
    assert cfg.live_request_generation_enabled is True
    assert cfg.live_demand_level == 'busy'
    assert cfg.live_request_rate_multiplier == 1.7
    assert cfg.max_generated_requests_per_tick == 5
