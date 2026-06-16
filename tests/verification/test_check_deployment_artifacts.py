from __future__ import annotations

import json
from pathlib import Path

from scripts.verification.check_deployment_artifacts import check_artifacts


REQUIRED_RELATIVE_PATHS = (
    "data/processed/evside_feeder_rl/manifest.json",
    "data/processed/evside_feeder_rl/feature_stats.json",
    "data/processed/evside_feeder_rl/feeder_ev_action_catalog.parquet",
    "data/processed/evside_feeder_rl/feeder_request_priors.parquet",
    "data/processed/evside_feeder_rl/feeder_grid_advisory_replay.parquet",
    "models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip",
)


def _write_complete_artifact_set(repo_root: Path) -> None:
    for relative_path in REQUIRED_RELATIVE_PATHS:
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text(
                json.dumps({"artifact": path.name}),
                encoding="utf-8",
            )
        else:
            path.write_bytes(b"deployment-artifact")


def test_missing_required_files_fail(tmp_path: Path) -> None:
    result = check_artifacts(tmp_path)

    assert result["passed"] is False
    assert result["summary"]["missing"] == len(REQUIRED_RELATIVE_PATHS)
    assert result["summary"]["invalid"] == 0


def test_valid_json_and_present_binary_artifacts_pass(tmp_path: Path) -> None:
    _write_complete_artifact_set(tmp_path)

    result = check_artifacts(tmp_path)

    assert result["passed"] is True
    assert result["summary"] == {
        "required": len(REQUIRED_RELATIVE_PATHS),
        "present": len(REQUIRED_RELATIVE_PATHS),
        "missing": 0,
        "invalid": 0,
        "parquet_checked": 0,
    }


def test_invalid_json_fails_with_clear_artifact_status(
    tmp_path: Path,
) -> None:
    _write_complete_artifact_set(tmp_path)
    manifest = (
        tmp_path
        / "data"
        / "processed"
        / "evside_feeder_rl"
        / "manifest.json"
    )
    manifest.write_text("{not-json", encoding="utf-8")

    result = check_artifacts(tmp_path)
    manifest_result = next(
        artifact
        for artifact in result["artifacts"]
        if artifact["path"].endswith("manifest.json")
    )

    assert result["passed"] is False
    assert result["summary"]["invalid"] == 1
    assert manifest_result["status"] == "invalid"
    assert manifest_result["error"].startswith("invalid JSON:")


def test_json_output_schema_uses_only_relative_paths(tmp_path: Path) -> None:
    _write_complete_artifact_set(tmp_path)

    result = check_artifacts(tmp_path)
    serialized = json.dumps(result, sort_keys=True)

    assert set(result) == {
        "passed",
        "check_parquet",
        "artifacts",
        "summary",
    }
    assert all(
        set(artifact) == {
            "path",
            "kind",
            "required",
            "exists",
            "size_bytes",
            "status",
            "error",
        }
        for artifact in result["artifacts"]
    )
    assert str(tmp_path) not in serialized
    assert "D:/" not in serialized
    assert "G:/" not in serialized


def test_unmaterialized_git_lfs_pointer_fails(tmp_path: Path) -> None:
    _write_complete_artifact_set(tmp_path)
    checkpoint = (
        tmp_path
        / "models"
        / "rl_feeder_final"
        / "maskable_ppo_feeder_station_selector.zip"
    )
    checkpoint.write_text(
        "\n".join(
            (
                "version https://git-lfs.github.com/spec/v1",
                "oid sha256:" + ("0" * 64),
                "size 3609626",
            )
        ),
        encoding="ascii",
    )

    result = check_artifacts(tmp_path)
    checkpoint_result = next(
        artifact
        for artifact in result["artifacts"]
        if artifact["kind"] == "checkpoint"
    )

    assert result["passed"] is False
    assert checkpoint_result["status"] == "invalid"
    assert checkpoint_result["error"] == (
        "Git LFS object is not materialized; run git lfs pull"
    )
