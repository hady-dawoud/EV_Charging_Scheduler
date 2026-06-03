from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run_import(code: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[2]
    pythonpath = str(repo_root / 'packages' / 'ev_core' / 'src')
    return subprocess.run(
        [sys.executable, '-c', code],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, 'PYTHONPATH': pythonpath},
    )


def test_importing_ev_core_config_is_dependency_light() -> None:
    code = """
import importlib
import sys
importlib.import_module('ev_core.config')
for banned in [
    'fastapi',
    'streamlit',
    'dashboards',
    'services.sim_runtime.storage',
    'gymnasium',
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
    assert 'ok' in result.stdout
