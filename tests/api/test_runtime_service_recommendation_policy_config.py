from __future__ import annotations

import importlib
import sys
import types

for module_name in ("numpy", "pandas"):
    try:
        importlib.import_module(module_name)
    except ImportError:
        module = types.ModuleType(module_name)
        module.DataFrame = object
        sys.modules.setdefault(module_name, module)


def test_api_runtime_manager_uses_recommendation_policy_env_var(monkeypatch) -> None:
    runtime_service = importlib.import_module("app.services.runtime_service")
    runtime_service.get_runtime_manager.cache_clear()
    seen_configs = []

    class FakeRuntimeManager:
        def __init__(self, *, repo_root, config=None) -> None:
            self.repo_root = repo_root
            self.config = config
            seen_configs.append(config)

    monkeypatch.setattr(runtime_service, "RuntimeManager", FakeRuntimeManager)
    monkeypatch.setenv("RECOMMENDATION_POLICY_NAME", "closest")

    manager = runtime_service.get_runtime_manager()

    assert manager.config is not None
    assert manager.config.recommendation_policy_name == "closest"
    assert manager.config.dynamic_pricing_enabled is True
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()


def test_api_runtime_manager_uses_forced_recommendation_policy_env_var(monkeypatch) -> None:
    runtime_service = importlib.import_module("app.services.runtime_service")
    runtime_service.get_runtime_manager.cache_clear()
    seen_configs = []

    class FakeRuntimeManager:
        def __init__(self, *, repo_root, config=None) -> None:
            self.repo_root = repo_root
            self.config = config
            seen_configs.append(config)

    monkeypatch.setattr(runtime_service, "RuntimeManager", FakeRuntimeManager)
    monkeypatch.setenv("RECOMMENDATION_POLICY_NAME", "closest")
    monkeypatch.setenv("FORCE_RECOMMENDATION_POLICY", "rl_maskable_ppo_feeder")
    monkeypatch.setenv("RL_FEEDER_CHECKPOINT_PATH", "models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip")
    monkeypatch.setenv("FEEDER_RL_DATA_DIR", "data/processed/evside_feeder_rl")
    monkeypatch.setenv("RL_POLICY_FAIL_CLOSED", "true")

    manager = runtime_service.get_runtime_manager()

    assert manager.config is not None
    assert manager.config.recommendation_policy_name == "rl_maskable_ppo_feeder"
    assert manager.config.requested_recommendation_policy_name == "closest"
    assert manager.config.force_recommendation_policy == "rl_maskable_ppo_feeder"
    assert manager.config.rl_feeder_checkpoint_path == "models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip"
    assert manager.config.feeder_data_dir == "data/processed/evside_feeder_rl"
    assert manager.config.rl_policy_fail_closed is True
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()


def test_api_runtime_manager_uses_rl_safety_env_vars(monkeypatch) -> None:
    runtime_service = importlib.import_module("app.services.runtime_service")
    runtime_service.get_runtime_manager.cache_clear()
    seen_configs = []

    class FakeRuntimeManager:
        def __init__(self, *, repo_root, config=None) -> None:
            self.repo_root = repo_root
            self.config = config
            seen_configs.append(config)

    monkeypatch.setattr(runtime_service, "RuntimeManager", FakeRuntimeManager)
    monkeypatch.setenv("RL_SAFETY_FILTER_ENABLED", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_MODE", "block")
    monkeypatch.setenv("RL_SAFETY_FILTER_STRICT", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_PENALTY_WEIGHT", "0.5")
    monkeypatch.setenv("RL_SAFETY_BLOCK_UNSAFE", "true")
    monkeypatch.setenv(
        "RL_SAFETY_MAPPING_MODE",
        "stable_ordinal_demo_bridge",
    )

    manager = runtime_service.get_runtime_manager()

    assert manager.config is not None
    assert manager.config.rl_safety_filter_enabled is True
    assert manager.config.rl_safety_filter_mode == "block"
    assert manager.config.rl_safety_filter_strict is True
    assert manager.config.rl_safety_filter_penalty_weight == 0.5
    assert manager.config.rl_safety_block_unsafe is True
    assert (
        manager.config.rl_safety_mapping_mode
        == "stable_ordinal_demo_bridge"
    )
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()


def test_api_runtime_manager_uses_dynamic_pricing_env_var(monkeypatch) -> None:
    runtime_service = importlib.import_module("app.services.runtime_service")
    runtime_service.get_runtime_manager.cache_clear()
    seen_configs = []

    class FakeRuntimeManager:
        def __init__(self, *, repo_root, config=None) -> None:
            self.repo_root = repo_root
            self.config = config
            seen_configs.append(config)

    monkeypatch.setattr(runtime_service, "RuntimeManager", FakeRuntimeManager)
    monkeypatch.setenv("DYNAMIC_PRICING_ENABLED", "false")

    manager = runtime_service.get_runtime_manager()

    assert manager.config is not None
    assert manager.config.dynamic_pricing_enabled is False
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()


def test_api_runtime_manager_uses_routing_env_vars(monkeypatch) -> None:
    runtime_service = importlib.import_module("app.services.runtime_service")
    runtime_service.get_runtime_manager.cache_clear()
    seen_configs = []

    class FakeRuntimeManager:
        def __init__(self, *, repo_root, config=None) -> None:
            self.repo_root = repo_root
            self.config = config
            seen_configs.append(config)

    monkeypatch.setattr(runtime_service, "RuntimeManager", FakeRuntimeManager)
    monkeypatch.setenv("ROUTING_PROVIDER_NAME", "osmnx")
    monkeypatch.setenv("OSMNX_GRAPH_PATH", "data/processed/routing/dundee_drive.graphml")

    manager = runtime_service.get_runtime_manager()

    assert manager.config is not None
    assert manager.config.routing_provider_name == "osmnx"
    assert manager.config.osmnx_graph_path == "data/processed/routing/dundee_drive.graphml"
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()


def test_api_runtime_manager_uses_forecast_env_vars(monkeypatch) -> None:
    runtime_service = importlib.import_module("app.services.runtime_service")
    runtime_service.get_runtime_manager.cache_clear()
    seen_configs = []

    class FakeRuntimeManager:
        def __init__(self, *, repo_root, config=None) -> None:
            self.repo_root = repo_root
            self.config = config
            seen_configs.append(config)

    monkeypatch.setattr(runtime_service, "RuntimeManager", FakeRuntimeManager)
    monkeypatch.setenv("FORECAST_PROVIDER", "keras_load_kw_30min")
    monkeypatch.setenv("FORECAST_MODEL_DIR", "models/forecasting/load_kw_30min")
    monkeypatch.setenv("FORECAST_RANKING_MODE", "metadata_only")
    monkeypatch.setenv("FORECAST_FAIL_CLOSED", "true")

    manager = runtime_service.get_runtime_manager()

    assert manager.config is not None
    assert manager.config.forecast_provider_name == "keras_load_kw_30min"
    assert manager.config.forecast_model_dir == "models/forecasting/load_kw_30min"
    assert manager.config.forecast_ranking_mode == "metadata_only"
    assert manager.config.forecast_fail_closed is True
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()
