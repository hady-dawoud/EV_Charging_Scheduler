from __future__ import annotations

import importlib
import sys
import types

for module_name in ("numpy", "pandas"):
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
