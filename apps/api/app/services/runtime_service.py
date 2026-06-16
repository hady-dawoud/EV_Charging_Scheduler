from __future__ import annotations

from functools import lru_cache

from app.bootstrap_paths import bootstrap_repo_paths

REPO_ROOT = bootstrap_repo_paths()

from ev_core.config.pricing import pricing_config_from_env
from ev_core.config.forecasting import forecasting_config_from_env
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
    forecasting_cfg = forecasting_config_from_env()
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
            recommendation_policy_name=recommendation_cfg.effective_env_policy_name,
            requested_recommendation_policy_name=recommendation_cfg.policy_name or None,
            force_recommendation_policy=recommendation_cfg.force_policy_name,
            rl_policy_fail_closed=recommendation_cfg.rl_policy_fail_closed,
            rl_feeder_checkpoint_path=(
                recommendation_cfg.rl_feeder_checkpoint_path.as_posix()
                if recommendation_cfg.rl_feeder_checkpoint_path is not None
                else None
            ),
            feeder_data_dir=(
                recommendation_cfg.feeder_data_dir.as_posix()
                if recommendation_cfg.feeder_data_dir is not None
                else None
            ),
            rl_safety_filter_enabled=recommendation_cfg.rl_safety_filter_enabled,
            rl_safety_filter_mode=recommendation_cfg.rl_safety_filter_mode,
            rl_safety_filter_strict=recommendation_cfg.rl_safety_filter_strict,
            rl_safety_filter_penalty_weight=(
                recommendation_cfg.rl_safety_filter_penalty_weight
            ),
            rl_safety_block_unsafe=recommendation_cfg.rl_safety_block_unsafe,
            rl_safety_mapping_mode=recommendation_cfg.rl_safety_mapping_mode,
            topology_scenario_id=topology_cfg.topology_scenario_id,
            dynamic_pricing_enabled=pricing_cfg.dynamic_pricing_enabled,
            routing_provider_name=routing_cfg.provider_name,
            osmnx_graph_path=osmnx_graph_path,
            forecast_provider_name=forecasting_cfg.provider_name,
            forecast_model_dir=forecasting_cfg.model_dir.as_posix(),
            forecast_ranking_mode=forecasting_cfg.ranking_mode,
            forecast_fail_closed=forecasting_cfg.fail_closed,
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
    policy_selection_metadata: dict | None = None,
) -> RecommendationResponse:
    ensure_runtime_started()
    return get_runtime_manager().inject_request(
        request,
        recommendation_policy_name=recommendation_policy_name,
        policy_selection_metadata=policy_selection_metadata,
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
