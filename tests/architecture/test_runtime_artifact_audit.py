from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_runtime_artifacts.py"


def test_runtime_artifact_audit_reports_present_and_missing_without_failing(tmp_path) -> None:
    present_artifact = tmp_path / "models" / "rl" / "maskable_ppo_station_selector.zip"
    present_artifact.parent.mkdir(parents=True)
    present_artifact.write_text("placeholder", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--repo-root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "PRESENT  models/rl/maskable_ppo_station_selector.zip" in result.stdout
    assert "MISSING  models/rl_feeder/maskable_ppo_feeder_station_selector.zip" in result.stdout
    assert "missing:" in result.stdout


def test_runtime_artifact_audit_strict_mode_fails_when_artifacts_are_missing(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--repo-root", str(tmp_path), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "MISSING  models/rl/maskable_ppo_station_selector.zip" in result.stdout
