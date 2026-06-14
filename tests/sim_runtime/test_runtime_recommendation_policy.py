from __future__ import annotations

import sys
import types
from datetime import datetime
from pathlib import Path
import importlib

for module_name in ("numpy", "pandas"):
    try:
        importlib.import_module(module_name)
    except ImportError:
        module = types.ModuleType(module_name)
        module.DataFrame = object
        sys.modules.setdefault(module_name, module)

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationResponse
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager


class FakeEnv:
    def __init__(self) -> None:
        self.seen_policy_name: str | None = None
        self.seen_policy_selection_metadata: dict | None = None
        self.injected_request: ExternalChargingRequest | None = None

    def inject_external_request(self, request: ExternalChargingRequest):
        self.injected_request = request
        return request

    def get_ranked_recommendations(
        self,
        request,
        recommendation_policy_name: str | None = None,
        policy_selection_metadata: dict | None = None,
    ):
        self.seen_policy_name = recommendation_policy_name
        self.seen_policy_selection_metadata = policy_selection_metadata
        return RecommendationResponse(
            request_id=request.request_id or "request-1",
            client_request_id=request.client_request_id,
            simulated_timestamp=request.request_timestamp,
            zone_id=request.zone_id,
            top_recommendation=None,
            alternatives=[],
            source_type=request.source_type,
        )


class FakeStorage:
    def __init__(self) -> None:
        self.saved_recommendation: RecommendationResponse | None = None

    def save_external_request(self, request: ExternalChargingRequest, *, status: str) -> None:
        self.saved_external_request = request
        self.saved_status = status

    def save_recommendation(self, response: RecommendationResponse) -> None:
        self.saved_recommendation = response


def request_payload() -> ExternalChargingRequest:
    return ExternalChargingRequest(
        client_request_id="client-1",
        request_timestamp=datetime(2024, 6, 10, 12, 0),
        requested_energy_kwh=20.0,
        preference_mode="closest",
        latest_finish_ts=datetime(2024, 6, 10, 14, 0),
        source_type="external_live",
        request_id="request-1",
        zone_id="zone",
    )


def runtime_manager_with_fake_env(
    env: FakeEnv,
    *,
    recommendation_policy_name: str = "cheapest",
) -> RuntimeManager:
    manager = RuntimeManager.__new__(RuntimeManager)
    manager.config = RuntimeConfig(recommendation_policy_name=recommendation_policy_name)
    manager.storage = FakeStorage()
    manager.forecast_diagnostics_provider = None
    manager._load_env = lambda: env
    manager._persist_env = lambda env, include_events=False: None
    return manager


def runtime_status_manager_with_fake_env(env: FakeEnv, config: RuntimeConfig) -> RuntimeManager:
    manager = RuntimeManager.__new__(RuntimeManager)
    manager.config = config
    manager.osmnx_graph_path = Path(__file__)
    return manager


def test_runtime_config_default_recommendation_policy_is_weighted_score() -> None:
    assert RuntimeConfig().recommendation_policy_name == "weighted_score"


def test_runtime_config_enables_dynamic_pricing_by_default() -> None:
    assert RuntimeConfig().dynamic_pricing_enabled is True


def test_runtime_config_rl_safety_defaults_are_disabled() -> None:
    config = RuntimeConfig()

    assert config.rl_safety_filter_enabled is False
    assert config.rl_safety_filter_mode == "penalty"
    assert config.rl_safety_filter_strict is False
    assert config.rl_safety_filter_penalty_weight == 0.25
    assert config.rl_safety_block_unsafe is False
    assert config.rl_safety_mapping_mode == "exact_only"
    assert config.recommendation_policy_name == "weighted_score"


def test_runtime_manager_inject_request_passes_configured_recommendation_policy() -> None:
    env = FakeEnv()
    manager = runtime_manager_with_fake_env(env, recommendation_policy_name="closest")

    manager.inject_request(request_payload())

    assert env.seen_policy_name == "closest"


def test_runtime_manager_recommend_passes_configured_recommendation_policy() -> None:
    env = FakeEnv()
    manager = runtime_manager_with_fake_env(env, recommendation_policy_name="overload_aware")

    manager.recommend(request_payload())

    assert env.seen_policy_name == "overload_aware"


def test_runtime_manager_per_call_policy_overrides_configured_policy() -> None:
    env = FakeEnv()
    manager = runtime_manager_with_fake_env(env, recommendation_policy_name="cheapest")

    manager.inject_request(request_payload(), recommendation_policy_name="fastest")

    assert env.seen_policy_name == "fastest"


def test_runtime_manager_adds_forecast_metadata_when_diagnostics_provider_is_enabled() -> None:
    env = FakeEnv()
    manager = runtime_manager_with_fake_env(env, recommendation_policy_name="closest")

    class FakeForecastDiagnosticsProvider:
        def smoke_forecast(self, timestamp, *, allow_smoke_template=False):
            return types.SimpleNamespace(
                metadata=lambda: {
                    "forecast_provider": "keras_load_kw_30min",
                    "forecast_status": "smoke_template",
                    "forecast_ranking_mode": "metadata_only",
                    "forecast_used_for_ranking": False,
                }
            )

    manager.forecast_diagnostics_provider = FakeForecastDiagnosticsProvider()

    manager.recommend(request_payload())

    assert env.seen_policy_selection_metadata is not None
    assert env.seen_policy_selection_metadata["forecast_provider"] == "keras_load_kw_30min"
    assert env.seen_policy_selection_metadata["forecast_used_for_ranking"] is False


def test_runtime_status_reports_policy_override_configuration() -> None:
    config = RuntimeConfig(
        recommendation_policy_name="rl_maskable_ppo_feeder",
        requested_recommendation_policy_name="closest",
        force_recommendation_policy="rl_maskable_ppo_feeder",
        rl_policy_fail_closed=True,
        rl_feeder_checkpoint_path="models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip",
        feeder_data_dir="data/processed/evside_feeder_rl",
    )
    env = types.SimpleNamespace(
        routing_provider=types.SimpleNamespace(name="simple_distance", is_available=lambda: True),
        runtime_mode="replay",
        running=True,
        requests={},
        active_sessions={},
        policy_mode="overload_aware",
        dynamic_pricing_enabled=True,
        last_routing_fallback_reason=None,
        demand_multiplier=1.0,
        warm_start_minutes=0,
        replay_year=2024,
        replay_day=datetime(2024, 6, 10).date(),
        operational_start_time=datetime(2024, 6, 10, 12, 0),
        current_time=datetime(2024, 6, 10, 12, 0),
        latest_external_request_id=None,
        completed_requests_total=0,
        missed_requests_total=0,
    )
    manager = runtime_status_manager_with_fake_env(env, config)

    status = manager._compose_runtime_status(env=env, loop_running=False, loop_interval_seconds=0)

    assert status["recommendation_policy_name"] == "rl_maskable_ppo_feeder"
    assert status["requested_recommendation_policy_name"] == "closest"
    assert status["force_recommendation_policy"] == "rl_maskable_ppo_feeder"
    assert status["policy_override_used"] is True
    assert status["rl_policy_fail_closed"] is True
    assert status["rl_feeder_checkpoint_path"] == "models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip"
    assert status["feeder_data_dir"] == "data/processed/evside_feeder_rl"


def test_runtime_status_reports_rl_safety_configuration() -> None:
    config = RuntimeConfig(
        rl_safety_filter_enabled=True,
        rl_safety_filter_mode="block",
        rl_safety_filter_strict=True,
        rl_safety_filter_penalty_weight=0.5,
        rl_safety_block_unsafe=True,
        rl_safety_mapping_mode="stable_ordinal_demo_bridge",
    )
    env = types.SimpleNamespace(
        routing_provider=types.SimpleNamespace(name="simple_distance", is_available=lambda: True),
        runtime_mode="replay",
        running=True,
        requests={},
        active_sessions={},
        policy_mode="overload_aware",
        dynamic_pricing_enabled=True,
        last_routing_fallback_reason=None,
        demand_multiplier=1.0,
        warm_start_minutes=0,
        replay_year=2024,
        replay_day=datetime(2024, 6, 10).date(),
        operational_start_time=datetime(2024, 6, 10, 12, 0),
        current_time=datetime(2024, 6, 10, 12, 0),
        latest_external_request_id=None,
        completed_requests_total=0,
        missed_requests_total=0,
    )
    manager = runtime_status_manager_with_fake_env(env, config)

    status = manager._compose_runtime_status(
        env=env,
        loop_running=False,
        loop_interval_seconds=0,
    )

    assert status["rl_safety_filter_enabled"] is True
    assert status["rl_safety_filter_mode"] == "block"
    assert status["rl_safety_filter_strict"] is True
    assert status["rl_safety_filter_penalty_weight"] == 0.5
    assert status["rl_safety_block_unsafe"] is True
    assert status["rl_safety_mapping_mode"] == "stable_ordinal_demo_bridge"


def test_runtime_policy_selection_metadata_includes_rl_safety_config() -> None:
    env = FakeEnv()
    manager = runtime_manager_with_fake_env(
        env,
        recommendation_policy_name="rl_safety_closest",
    )
    manager.config = RuntimeConfig(
        recommendation_policy_name="rl_safety_closest",
        requested_recommendation_policy_name="closest",
        rl_safety_filter_enabled=True,
        rl_safety_filter_mode="penalty",
        rl_safety_filter_strict=True,
        rl_safety_filter_penalty_weight=0.5,
        rl_safety_block_unsafe=True,
        rl_safety_mapping_mode="stable_ordinal_demo_bridge",
    )

    manager.recommend(request_payload())

    assert env.seen_policy_name == "rl_safety_closest"
    assert env.seen_policy_selection_metadata is not None
    assert (
        env.seen_policy_selection_metadata["requested_policy_name"]
        == "closest"
    )
    assert (
        env.seen_policy_selection_metadata["effective_policy_name"]
        == "rl_safety_closest"
    )
    assert (
        env.seen_policy_selection_metadata["rl_safety_filter_enabled"]
        is True
    )
    assert (
        env.seen_policy_selection_metadata["rl_safety_filter_mode"]
        == "penalty"
    )
    assert (
        env.seen_policy_selection_metadata["rl_safety_filter_strict"]
        is True
    )
    assert (
        env.seen_policy_selection_metadata[
            "rl_safety_filter_penalty_weight"
        ]
        == 0.5
    )
    assert (
        env.seen_policy_selection_metadata["rl_safety_block_unsafe"]
        is True
    )
    assert (
        env.seen_policy_selection_metadata["rl_safety_mapping_mode"]
        == "stable_ordinal_demo_bridge"
    )
