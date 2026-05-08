from __future__ import annotations

import os
from functools import lru_cache

from app.bootstrap_paths import bootstrap_repo_paths

REPO_ROOT = bootstrap_repo_paths()

from ev_core.contracts.events import RuntimeEvent
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationResponse, StateSnapshot
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager


class RuntimeNotStartedError(RuntimeError):
    pass


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


@lru_cache(maxsize=1)
def get_runtime_manager() -> RuntimeManager:
    return RuntimeManager(
        repo_root=REPO_ROOT,
        config=RuntimeConfig(
            recommendation_policy_name=os.getenv("RECOMMENDATION_POLICY_NAME", "weighted_score"),
            topology_scenario_id=os.getenv("TOPOLOGY_SCENARIO_ID") or None,
            dynamic_pricing_enabled=_env_flag("DYNAMIC_PRICING_ENABLED", True),
        ),
    )


def ensure_runtime_started() -> None:
    state = get_runtime_manager().get_latest_state()
    if state is None:
        raise RuntimeNotStartedError(
            "Simulator runtime is not started. Start services.sim_runtime first."
        )


def inject_live_request(
    request: ExternalChargingRequest,
    *,
    recommendation_policy_name: str | None = None,
) -> RecommendationResponse:
    ensure_runtime_started()
    return get_runtime_manager().inject_request(
        request,
        recommendation_policy_name=recommendation_policy_name,
    )


def get_runtime_status() -> dict:
    return get_runtime_manager().get_runtime_status()


def get_runtime_state() -> StateSnapshot:
    ensure_runtime_started()
    state = get_runtime_manager().get_latest_state()
    if state is None:
        raise RuntimeNotStartedError(
            "Simulator runtime is not started. Start services.sim_runtime first."
        )
    return state


def get_recent_events(limit: int = 50) -> list[RuntimeEvent]:
    ensure_runtime_started()
    return list(get_runtime_manager().get_recent_events(limit=limit))


def get_recent_recommendations(limit: int = 20) -> list[RecommendationResponse]:
    ensure_runtime_started()
    return get_runtime_manager().get_recent_recommendations(limit=limit)
