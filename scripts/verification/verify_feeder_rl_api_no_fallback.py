"""Verify feeder RL safety through the in-process API/runtime path."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import gc
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEEDER_DATA_DIR = (
    REPO_ROOT / "data" / "processed" / "evside_feeder_rl"
)
DEFAULT_CHECKPOINT_PATH = (
    REPO_ROOT
    / "models"
    / "rl_feeder_final"
    / "maskable_ppo_feeder_station_selector.zip"
)
REQUIRED_FEEDER_FILES = (
    "manifest.json",
    "feature_stats.json",
    "feeder_ev_action_catalog.parquet",
    "feeder_request_priors.parquet",
    "feeder_grid_advisory_replay.parquet",
)
LIMITATIONS = (
    "offline recorded feeder context",
    "stable ordinal bridge is nonphysical app/demo mapping",
    "in-process API/runtime verification without an external server",
    "not live DigitalTwin closed-loop PF/OPF or MARL evidence",
)


class VerifierFailure(AssertionError):
    """Raised when a required no-fallback verifier contract is not met."""


def check_required_artifacts(
    *,
    base_dir: Path,
    checkpoint_path: Path,
    strict: bool,
) -> dict[str, Any]:
    files = {
        name: {
            "exists": (base_dir / name).is_file(),
            "path": (base_dir / name).as_posix(),
        }
        for name in REQUIRED_FEEDER_FILES
    }
    checkpoint = {
        "exists": checkpoint_path.is_file(),
        "path": checkpoint_path.as_posix(),
    }
    missing = [
        item["path"]
        for item in files.values()
        if not item["exists"]
    ]
    if strict and not checkpoint["exists"]:
        missing.append(checkpoint["path"])
    if missing:
        raise VerifierFailure(
            "missing required feeder artifacts: " + ", ".join(missing)
        )
    return {
        "ok": True,
        "base_dir": base_dir.as_posix(),
        "files": files,
        "checkpoint": checkpoint,
    }


def render_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def validate_no_fallback_contract(
    *,
    response_metadata: Mapping[str, Any],
    option_metadata: list[Mapping[str, Any]],
    strict: bool,
) -> dict[str, Any]:
    policy = str(
        response_metadata.get("effective_policy_name")
        or response_metadata.get("policy_name")
        or ""
    )
    if not policy.startswith("rl_safety_"):
        raise VerifierFailure(
            f"no silent deterministic fallback allowed; got policy {policy!r}"
        )
    if response_metadata.get("rl_safety_filter_enabled") is not True:
        raise VerifierFailure("RL safety filter was not reported as enabled")
    if response_metadata.get("rl_safety_filter_applied") is not True:
        raise VerifierFailure("RL safety filter was not applied")

    response_fallback = response_metadata.get("fallback_used")
    safety_fallback = response_metadata.get(
        "rl_safety_filter_fallback_used"
    )
    if response_fallback is True or safety_fallback is True:
        raise VerifierFailure("response reported fallback_used=true")
    if safety_fallback is not False:
        raise VerifierFailure(
            "response is missing required rl_safety_filter_fallback_used=false"
        )

    if not option_metadata:
        raise VerifierFailure("API/runtime response contains no recommendations")
    required_safety_keys = (
        "rl_safety_filter_enabled",
        "rl_safety_status",
        "rl_safety_score",
    )
    for index, metadata in enumerate(option_metadata):
        if metadata.get("fallback_used") is not False:
            raise VerifierFailure(
                f"recommendation option {index} reported fallback"
            )
        missing = [
            key for key in required_safety_keys if key not in metadata
        ]
        if missing:
            raise VerifierFailure(
                "recommendation option "
                f"{index} missing safety metadata: {', '.join(missing)}"
            )

    observation_shape = response_metadata.get("feeder_observation_shape")
    action_count = response_metadata.get("feeder_action_count")
    valid_action_count = response_metadata.get(
        "feeder_valid_action_count"
    )
    selected_action_index = response_metadata.get(
        "rl_selected_action_index"
    )
    selected_station_id = response_metadata.get(
        "rl_selected_feeder_station_id"
    )
    checkpoint_path = response_metadata.get("rl_feeder_checkpoint_path")
    if strict:
        if observation_shape != [2200]:
            raise VerifierFailure(
                "strict verifier expected observation shape [2200], "
                f"got {observation_shape!r}"
            )
        if action_count != 73:
            raise VerifierFailure(
                f"strict verifier expected 73 actions, got {action_count!r}"
            )
        if not isinstance(valid_action_count, int) or valid_action_count <= 0:
            raise VerifierFailure(
                "strict verifier requires at least one valid action"
            )
        if not isinstance(selected_action_index, int):
            raise VerifierFailure(
                "strict verifier missing selected action index"
            )
        if not selected_station_id:
            raise VerifierFailure(
                "strict verifier missing selected feeder station"
            )
        if not checkpoint_path:
            raise VerifierFailure(
                "strict verifier missing checkpoint metadata"
            )

    return {
        "api_check": {
            "ok": True,
            "policy": policy,
            "fallback_used": response_fallback,
            "rl_safety_filter_fallback_used": safety_fallback,
            "safety_metadata_present": True,
            "metadata_keys": sorted(str(key) for key in response_metadata),
        },
        "checkpoint": {
            "observation_shape": observation_shape,
            "action_count": action_count,
            "valid_action_count": valid_action_count,
            "selected_action_index": selected_action_index,
            "selected_station_id": selected_station_id,
            "checkpoint_path": checkpoint_path,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def run_verification(*, strict: bool) -> dict[str, Any]:
    artifact_check = check_required_artifacts(
        base_dir=DEFAULT_FEEDER_DATA_DIR,
        checkpoint_path=DEFAULT_CHECKPOINT_PATH,
        strict=strict,
    )
    if strict:
        _require_optional_dependencies()

    _configure_runtime_paths()
    from app.services import recommendations_service, runtime_service
    from ev_core.contracts.requests import ExternalChargingRequest
    from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager
    from services.sim_runtime.storage import RuntimeStorage

    verifier_env = {
        "RECOMMENDATION_POLICY_NAME": "rl_safety_preference",
        "RL_SAFETY_FILTER_ENABLED": "true",
        "RL_SAFETY_FILTER_MODE": "penalty",
        "RL_SAFETY_FILTER_STRICT": "true" if strict else "false",
        "RL_SAFETY_BLOCK_UNSAFE": "false",
        "RL_SAFETY_FILTER_PENALTY_WEIGHT": "0.25",
        "RL_SAFETY_MAPPING_MODE": "stable_ordinal_demo_bridge",
        "RL_FEEDER_CHECKPOINT_PATH": str(DEFAULT_CHECKPOINT_PATH),
        "FEEDER_RL_DATA_DIR": str(DEFAULT_FEEDER_DATA_DIR),
        "GRID_ADVISORY_MODE": "recorded",
        "GRID_ADVISORY_REPLAY_DIR": str(DEFAULT_FEEDER_DATA_DIR),
        "RL_POLICY_FAIL_CLOSED": "true" if strict else "false",
    }
    with temporary_runtime_root() as temp_dir, _temporary_environment(
        verifier_env
    ):
        manager = RuntimeManager(
            REPO_ROOT,
            config=RuntimeConfig(
                recommendation_policy_name="rl_safety_preference",
                requested_recommendation_policy_name=(
                    "rl_safety_preference"
                ),
                rl_policy_fail_closed=strict,
                rl_feeder_checkpoint_path=str(DEFAULT_CHECKPOINT_PATH),
                feeder_data_dir=str(DEFAULT_FEEDER_DATA_DIR),
                rl_safety_filter_enabled=True,
                rl_safety_filter_mode="penalty",
                rl_safety_filter_strict=strict,
                rl_safety_filter_penalty_weight=0.25,
                rl_safety_block_unsafe=False,
                rl_safety_mapping_mode=(
                    "stable_ordinal_demo_bridge"
                ),
            ),
        )
        manager.storage = RuntimeStorage(Path(temp_dir))
        manager.start(
            replay_day="2024-06-10",
            start_hour=12,
            start_minute=0,
            warm_start_hours=0,
        )

        original_get_runtime_manager = runtime_service.get_runtime_manager
        runtime_service.get_runtime_manager = lambda: manager
        try:
            response = recommendations_service.generate_recommendations(
                ExternalChargingRequest(
                    client_request_id="verify-feeder-rl-api-no-fallback",
                    request_id="verify-feeder-rl-api-no-fallback",
                    request_timestamp=datetime(2024, 6, 10, 12, 0),
                    current_latitude=56.462,
                    current_longitude=-2.9707,
                    target_soc=80.0,
                    current_soc=45.0,
                    battery_kwh=60.0,
                    requested_energy_kwh=21.0,
                    preference_mode="closest",
                    charger_type="Any",
                    latest_finish_ts=(
                        datetime(2024, 6, 10, 12, 0)
                        + timedelta(hours=3)
                    ),
                    source_type="external_live",
                    zone_id="zone_central_waterfront",
                    metadata={
                        "verification_script": Path(__file__).name,
                    },
                )
            )
        finally:
            runtime_service.get_runtime_manager = (
                original_get_runtime_manager
            )
        manager = None
        gc.collect()

    options = [
        option
        for option in [
            response.top_recommendation,
            *response.alternatives,
        ]
        if option is not None
    ]
    contract = validate_no_fallback_contract(
        response_metadata=response.metadata,
        option_metadata=[option.metadata for option in options],
        strict=strict,
    )
    contract["api_check"].update(
        {
            "request_id": response.request_id,
            "recommendation_count": len(options),
            "top_station_id": (
                response.top_recommendation.station_id
                if response.top_recommendation is not None
                else None
            ),
            "integration_path": (
                "app.services.recommendations_service"
                " -> app.services.runtime_service"
                " -> services.sim_runtime.RuntimeManager"
            ),
        }
    )
    return {
        "passed": True,
        "strict": strict,
        "artifact_check": artifact_check,
        **contract,
        "limitations": list(LIMITATIONS),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_verification(strict=args.strict)
    except Exception as exc:
        print(
            render_json(
                {
                    "passed": False,
                    "strict": args.strict,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "limitations": list(LIMITATIONS),
                }
            )
        )
        return 1
    print(render_json(result))
    return 0


def _configure_runtime_paths() -> None:
    paths = (
        REPO_ROOT,
        REPO_ROOT / "packages" / "ev_core" / "src",
        REPO_ROOT / "apps" / "api",
    )
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _require_optional_dependencies() -> None:
    missing = []
    for module_name in ("torch", "stable_baselines3", "sb3_contrib"):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        raise VerifierFailure(
            "strict verifier requires optional packages: "
            + ", ".join(missing)
        )


@contextmanager
def _temporary_environment(values: Mapping[str, str]):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def temporary_runtime_root():
    root = Path(
        tempfile.mkdtemp(prefix="ev-smart-charging-phase-g-")
    )
    try:
        yield root
    finally:
        for attempt in range(5):
            gc.collect()
            try:
                shutil.rmtree(root)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.1 * (attempt + 1))


if __name__ == "__main__":
    raise SystemExit(main())
