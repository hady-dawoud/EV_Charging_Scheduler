from __future__ import annotations

from functools import lru_cache

from app.bootstrap_paths import bootstrap_repo_paths

REPO_ROOT = bootstrap_repo_paths()

from ev_core.config.pricing import pricing_config_from_env
from ev_core.config.recommendation import recommendation_config_from_env
from ev_core.config.routing import routing_config_from_env
from ev_core.config.topology import topology_config_from_env
from ev_core.contracts.events import RuntimeEvent
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationResponse, StateSnapshot
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager


class RuntimeNotStartedError(RuntimeError):
    pass
@lru_cache(maxsize=1)
def get_runtime_manager() -> RuntimeManager:
    recommendation_cfg = recommendation_config_from_env()
    routing_cfg = routing_config_from_env()
    pricing_cfg = pricing_config_from_env()
    topology_cfg = topology_config_from_env()
    osmnx_graph_path = (
        routing_cfg.osmnx_graph_path.as_posix()
        if routing_cfg.osmnx_graph_path is not None
        else "data/processed/routing/dundee_drive.graphml"
    )
    return RuntimeManager(
        repo_root=REPO_ROOT,
        config=RuntimeConfig(
            recommendation_policy_name=recommendation_cfg.policy_name,
            topology_scenario_id=topology_cfg.topology_scenario_id,
            dynamic_pricing_enabled=pricing_cfg.dynamic_pricing_enabled,
            routing_provider_name=routing_cfg.provider_name,
            osmnx_graph_path=osmnx_graph_path,
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
