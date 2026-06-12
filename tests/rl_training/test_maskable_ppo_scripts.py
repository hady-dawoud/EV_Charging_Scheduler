from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_train_maskable_ppo_script_dry_run_does_not_train() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "rl_training" / "train_maskable_ppo_station_selector.py"),
            "--dry-run",
            "--scenario-count",
            "1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "dry_run: no training performed" in result.stdout


def test_evaluate_maskable_ppo_script_dry_run_does_not_load_checkpoint() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "rl_training" / "evaluate_maskable_ppo_station_selector.py"),
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "dry_run: no checkpoint loaded" in result.stdout
