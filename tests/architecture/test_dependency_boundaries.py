from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run_import(code: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[2]
    pythonpath = str(repo_root / "packages" / "ev_core" / "src")
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


def test_boundary_packages_import() -> None:
    code = """
import importlib
for name in [
    'ev_core.digital_twin',
    'ev_core.rl_training',
    'ev_core.benchmarks',
    'ev_core.deployment',
]:
    importlib.import_module(name)
print('ok')
"""
    result = _run_import(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_rl_training_import_does_not_pull_app_or_runtime_modules() -> None:
    code = """
import importlib
import sys
importlib.import_module('ev_core.rl_training')
for banned in [
    'fastapi',
    'streamlit',
    'apps',
    'dashboards',
    'services.sim_runtime.storage',
]:
    if banned in sys.modules:
        raise RuntimeError(f'banned module imported: {banned}')
print('ok')
"""
    result = _run_import(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_benchmarks_import_has_no_required_ev2gym_or_sustaingym() -> None:
    code = """
import importlib
importlib.import_module('ev_core.benchmarks')
print('ok')
"""
    result = _run_import(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
