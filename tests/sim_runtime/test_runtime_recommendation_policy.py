from __future__ import annotations

import sys
import types
from datetime import datetime

for module_name in ("numpy", "pandas"):
    module = types.ModuleType(module_name)
    module.DataFrame = object
    sys.modules.setdefault(module_name, module)

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import RecommendationResponse
from services.sim_runtime.runtime_manager import RuntimeConfig, RuntimeManager


class FakeEnv:
    def __init__(self) -> None:
        self.seen_policy_name: str | None = None
        self.injected_request: ExternalChargingRequest | None = None

    def inject_external_request(self, request: ExternalChargingRequest):
        self.injected_request = request
        return request

    def get_ranked_recommendations(self, request, recommendation_policy_name: str | None = None):
        self.seen_policy_name = recommendation_policy_name
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
    manager._load_env = lambda: env
    manager._persist_env = lambda env, include_events=False: None
    return manager


def test_runtime_config_default_recommendation_policy_is_weighted_score() -> None:
    assert RuntimeConfig().recommendation_policy_name == "weighted_score"


def test_runtime_config_enables_dynamic_pricing_by_default() -> None:
    assert RuntimeConfig().dynamic_pricing_enabled is True


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
