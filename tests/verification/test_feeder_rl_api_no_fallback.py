from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import scripts.verification.verify_feeder_rl_api_no_fallback as verifier
from scripts.verification.verify_feeder_rl_api_no_fallback import (
    VerifierFailure,
    check_required_artifacts,
    render_json,
    temporary_runtime_root,
    validate_no_fallback_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_module_import_keeps_optional_ml_dependencies_lazy() -> None:
    code = """
import json
import sys

import scripts.verification.verify_feeder_rl_api_no_fallback

print(json.dumps({
    name: name in sys.modules
    for name in ("torch", "stable_baselines3", "sb3_contrib")
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "torch": False,
        "stable_baselines3": False,
        "sb3_contrib": False,
    }


def test_missing_artifact_detection_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(VerifierFailure, match="missing required feeder artifacts"):
        check_required_artifacts(
            base_dir=tmp_path,
            checkpoint_path=tmp_path / "missing-checkpoint.zip",
            strict=True,
        )


def test_render_json_returns_parseable_contract() -> None:
    payload = {
        "passed": True,
        "strict": True,
        "api_check": {"ok": True, "fallback_used": False},
    }

    assert json.loads(render_json(payload)) == payload


def _response_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "effective_policy_name": "rl_safety_preference",
        "rl_safety_filter_enabled": True,
        "rl_safety_filter_applied": True,
        "fallback_used": False,
        "rl_safety_filter_fallback_used": False,
        "rl_feeder_checkpoint_path": (
            "models/rl_feeder_final/"
            "maskable_ppo_feeder_station_selector.zip"
        ),
        "feeder_observation_shape": [2200],
        "feeder_action_count": 73,
        "feeder_valid_action_count": 21,
        "rl_selected_action_index": 53,
        "rl_selected_feeder_station_id": "feeder-station-53",
    }
    metadata.update(overrides)
    return metadata


def _option_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "fallback_used": False,
        "rl_safety_filter_enabled": True,
        "rl_safety_status": "safe",
        "rl_safety_score": 1.0,
    }
    metadata.update(overrides)
    return metadata


def test_fallback_detection_fails_when_any_fallback_flag_is_true() -> None:
    with pytest.raises(VerifierFailure, match="fallback"):
        validate_no_fallback_contract(
            response_metadata=_response_metadata(fallback_used=True),
            option_metadata=[_option_metadata()],
            strict=True,
        )


def test_no_fallback_detection_passes_with_safety_metadata() -> None:
    result = validate_no_fallback_contract(
        response_metadata=_response_metadata(),
        option_metadata=[_option_metadata()],
        strict=True,
    )

    assert result["api_check"]["ok"] is True
    assert result["api_check"]["fallback_used"] is False
    assert result["api_check"]["rl_safety_filter_fallback_used"] is False
    assert result["checkpoint"]["observation_shape"] == [2200]
    assert result["checkpoint"]["action_count"] == 73
    assert result["checkpoint"]["valid_action_count"] == 21
    assert result["checkpoint"]["selected_action_index"] == 53


def test_temporary_runtime_root_retries_transient_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_rmtree = verifier.shutil.rmtree
    attempts = 0

    def flaky_rmtree(path: str | Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("temporary sqlite file is still closing")
        real_rmtree(path)

    monkeypatch.setattr(verifier.shutil, "rmtree", flaky_rmtree)

    with temporary_runtime_root() as runtime_root:
        (runtime_root / "marker.txt").write_text("ok", encoding="utf-8")

    assert attempts == 2
    assert not runtime_root.exists()
