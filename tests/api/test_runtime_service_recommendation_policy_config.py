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
    assert seen_configs == [manager.config]
    runtime_service.get_runtime_manager.cache_clear()
