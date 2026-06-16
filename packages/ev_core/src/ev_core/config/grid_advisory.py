from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .runtime import bool_from_env


def _path_from_env(value: str | None) -> Path | None:
    if value is None or not value.strip():
        return None
    return Path(value).expanduser()


@dataclass(frozen=True)
class GridAdvisoryConfig:
    mode: str = "disabled"
    replay_dir: Path | None = None
    base_url: str = "http://127.0.0.1:8091"
    timeout_seconds: float = 2.0
    hard_gate_runtime_rejects: bool = False
    fail_closed: bool = False


def grid_advisory_config_from_env() -> GridAdvisoryConfig:
    mode = os.getenv("GRID_ADVISORY_MODE", "disabled")
    default_url = "http://127.0.0.1:8088" if mode.strip().lower() == "runtime_http" else "http://127.0.0.1:8091"
    return GridAdvisoryConfig(
        mode=mode,
        replay_dir=_path_from_env(os.getenv("GRID_ADVISORY_REPLAY_DIR")),
        base_url=os.getenv("GRID_ADVISORY_BASE_URL", default_url),
        timeout_seconds=float(os.getenv("GRID_ADVISORY_TIMEOUT_SECONDS", "2.0")),
        hard_gate_runtime_rejects=bool_from_env(os.getenv("GRID_ADVISORY_HARD_GATE"), False),
        fail_closed=bool_from_env(os.getenv("GRID_ADVISORY_FAIL_CLOSED"), False),
    )


__all__ = ["GridAdvisoryConfig", "grid_advisory_config_from_env"]
