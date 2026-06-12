from __future__ import annotations

from pathlib import Path


def test_grid_advisory_config_from_env(monkeypatch) -> None:
    from ev_core.config.grid_advisory import grid_advisory_config_from_env

    monkeypatch.setenv("GRID_ADVISORY_MODE", "recorded")
    monkeypatch.setenv("GRID_ADVISORY_REPLAY_DIR", "outputs/grid_advisory_replay")
    monkeypatch.setenv("GRID_ADVISORY_BASE_URL", "http://127.0.0.1:8091")
    monkeypatch.setenv("GRID_ADVISORY_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("GRID_ADVISORY_HARD_GATE", "true")

    config = grid_advisory_config_from_env()

    assert config.mode == "recorded"
    assert config.replay_dir == Path("outputs/grid_advisory_replay")
    assert config.base_url == "http://127.0.0.1:8091"
    assert config.timeout_seconds == 3.5
    assert config.hard_gate_runtime_rejects is True
