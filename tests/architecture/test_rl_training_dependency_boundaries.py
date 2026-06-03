from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_import(code: str) -> subprocess.CompletedProcess[str]:
    pythonpath = str(REPO_ROOT / "packages" / "ev_core" / "src")
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": pythonpath,
        },
    )


def test_ev_core_rl_training_submodules_remain_dependency_light() -> None:
    code = """
import importlib
import sys
for name in [
    'ev_core.rl_training',
    'ev_core.rl_training.data_adapter',
    'ev_core.rl_training.scenario_factory',
    'ev_core.rl_training.offline_station_selection_env',
    'ev_core.rl_training.rollout',
    'ev_core.rl_training.metrics',
]:
    importlib.import_module(name)
for banned in [
    'fastapi',
    'streamlit',
    'apps',
    'dashboards',
    'services.sim_runtime.storage',
    'stable_baselines3',
    'sb3_contrib',
    'ev2gym',
    'sustaingym',
]:
    if banned in sys.modules:
        raise RuntimeError(f'banned module imported: {banned}')
print('ok')
"""
    result = _run_import(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_rl_training_verification_wrapper_points_to_grouped_script() -> None:
    wrapper_path = REPO_ROOT / "scripts" / "verify_offline_rl_training_env.py"

    assert wrapper_path.is_file(), wrapper_path
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert "Backward-compatible entrypoint" in wrapper_text
    assert "Wrapper target: scripts/rl_training/verify_offline_rl_training_env.py" in wrapper_text
