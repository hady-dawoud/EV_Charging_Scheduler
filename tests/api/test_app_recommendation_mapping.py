from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from ev_core.config.recommendation import (
    KNOWN_RECOMMENDATION_POLICIES,
    RecommendationConfig,
    select_recommendation_policy,
)
from ev_core.contracts.requests import ExternalChargingRequest


def external_payload(**overrides):
    now = datetime(2024, 6, 10, 12, 0)
    payload = {
        "client_request_id": "client-1",
        "request_timestamp": now,
        "current_latitude": 56.462,
        "current_longitude": -2.9707,
        "requested_energy_kwh": 20.0,
        "preference_mode": "closest",
        "charger_type": "Any",
        "latest_finish_ts": now + timedelta(hours=3),
        "source_type": "external_live",
        "request_id": "request-1",
        "zone_id": "zone_central_waterfront",
    }
    payload.update(overrides)
    return payload


def import_recommendations_service(monkeypatch: pytest.MonkeyPatch):
    fake_runtime_service = types.ModuleType("app.services.runtime_service")
    fake_runtime_service.inject_live_request = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.services.runtime_service", fake_runtime_service)
    monkeypatch.delitem(sys.modules, "app.services.recommendations_service", raising=False)
    return importlib.import_module("app.services.recommendations_service")


def clear_recommendation_policy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "FORCE_RECOMMENDATION_POLICY",
        "RECOMMENDATION_POLICY_NAME",
        "RL_SAFETY_FILTER_ENABLED",
        "RL_SAFETY_FILTER_MODE",
        "RL_SAFETY_FILTER_STRICT",
        "RL_SAFETY_FILTER_PENALTY_WEIGHT",
        "RL_SAFETY_BLOCK_UNSAFE",
        "RL_SAFETY_MAPPING_MODE",
        "RL_POLICY_FAIL_CLOSED",
        "RL_FEEDER_CHECKPOINT_PATH",
        "FEEDER_RL_DATA_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


def test_policy_env_reset_isolates_invalid_ambient_safety_config(monkeypatch) -> None:
    ambient_values = {
        "FORCE_RECOMMENDATION_POLICY": "rl_safety_preference",
        "RECOMMENDATION_POLICY_NAME": "weighted_score",
        "RL_SAFETY_FILTER_ENABLED": "true",
        "RL_SAFETY_FILTER_MODE": "invalid",
        "RL_SAFETY_FILTER_STRICT": "true",
        "RL_SAFETY_FILTER_PENALTY_WEIGHT": "not-a-number",
        "RL_SAFETY_BLOCK_UNSAFE": "true",
        "RL_SAFETY_MAPPING_MODE": "invalid",
        "RL_POLICY_FAIL_CLOSED": "true",
        "RL_FEEDER_CHECKPOINT_PATH": "models/ambient-checkpoint.zip",
        "FEEDER_RL_DATA_DIR": "data/ambient-feeder",
    }
    for name, value in ambient_values.items():
        monkeypatch.setenv(name, value)

    clear_recommendation_policy_env(monkeypatch)
    recommendations_service = import_recommendations_service(monkeypatch)
    seen = {}

    def fake_inject_live_request(
        request,
        *,
        recommendation_policy_name=None,
        policy_selection_metadata=None,
    ):
        seen["recommendation_policy_name"] = recommendation_policy_name
        seen["policy_selection_metadata"] = policy_selection_metadata
        return None

    monkeypatch.setattr(
        recommendations_service,
        "inject_live_request",
        fake_inject_live_request,
    )
    request = ExternalChargingRequest.model_validate(
        external_payload(preference_mode="Cheapest")
    )

    recommendations_service.generate_recommendations(request)

    assert seen["recommendation_policy_name"] == "cheapest"
    assert seen["policy_selection_metadata"]["rl_safety_filter_enabled"] is False
    assert seen["policy_selection_metadata"]["rl_safety_filter_mode"] == "penalty"
    assert seen["policy_selection_metadata"]["rl_safety_filter_strict"] is False
    assert seen["policy_selection_metadata"][
        "rl_safety_filter_penalty_weight"
    ] == 0.25
    assert seen["policy_selection_metadata"]["rl_safety_block_unsafe"] is False
    assert seen["policy_selection_metadata"]["rl_safety_mapping_mode"] == "exact_only"
    assert seen["policy_selection_metadata"]["rl_policy_fail_closed"] is False
    assert seen["policy_selection_metadata"]["rl_feeder_checkpoint_path"] is None
    assert seen["policy_selection_metadata"]["feeder_data_dir"] is None


@pytest.mark.parametrize(
    ("app_value", "policy_name"),
    [
        ("Cheapest", "cheapest"),
        ("Fastest", "fastest"),
        ("Closest", "closest"),
        ("cheapest", "cheapest"),
        ("fastest", "fastest"),
        ("closest", "closest"),
    ],
)
def test_external_request_app_preference_values_normalize_to_policy_names(app_value: str, policy_name: str) -> None:
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode=app_value))

    assert request.preference_mode == policy_name
    assert request.preference_mode in KNOWN_RECOMMENDATION_POLICIES


def test_external_request_invalid_preference_mode_fails_clearly() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExternalChargingRequest.model_validate(external_payload(preference_mode="Greenest"))

    message = str(exc_info.value)
    assert "preference_mode" in message
    assert "closest" in message
    assert "cheapest" in message
    assert "fastest" in message


def test_recommendations_service_maps_app_preference_to_recommender_policy(monkeypatch) -> None:
    clear_recommendation_policy_env(monkeypatch)
    recommendations_service = import_recommendations_service(monkeypatch)
    seen = {}

    def fake_inject_live_request(request, *, recommendation_policy_name=None, policy_selection_metadata=None):
        seen["request"] = request
        seen["recommendation_policy_name"] = recommendation_policy_name
        seen["policy_selection_metadata"] = policy_selection_metadata
        return None

    monkeypatch.setattr(recommendations_service, "inject_live_request", fake_inject_live_request)
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode="Cheapest"))

    recommendations_service.generate_recommendations(request)

    assert seen["request"] is request
    assert seen["recommendation_policy_name"] == "cheapest"
    assert seen["policy_selection_metadata"]["policy_source"] == "preference_mode"


def test_recommendation_policy_env_var_wins_over_app_preference(monkeypatch) -> None:
    clear_recommendation_policy_env(monkeypatch)
    recommendations_service = import_recommendations_service(monkeypatch)
    seen = {}

    def fake_inject_live_request(request, *, recommendation_policy_name=None, policy_selection_metadata=None):
        seen["request"] = request
        seen["recommendation_policy_name"] = recommendation_policy_name
        seen["policy_selection_metadata"] = policy_selection_metadata
        return None

    monkeypatch.setattr(recommendations_service, "inject_live_request", fake_inject_live_request)
    monkeypatch.setenv("RECOMMENDATION_POLICY_NAME", "rl_maskable_ppo_feeder")
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode="Cheapest"))

    recommendations_service.generate_recommendations(request)

    assert seen["request"] is request
    assert seen["recommendation_policy_name"] == "rl_maskable_ppo_feeder"
    assert seen["policy_selection_metadata"]["policy_source"] == "recommendation_policy_name"
    assert request.preference_mode == "cheapest"


def test_explicit_weighted_policy_env_reports_override_used(monkeypatch) -> None:
    clear_recommendation_policy_env(monkeypatch)
    recommendations_service = import_recommendations_service(monkeypatch)
    seen = {}

    def fake_inject_live_request(
        request,
        *,
        recommendation_policy_name=None,
        policy_selection_metadata=None,
    ):
        seen["recommendation_policy_name"] = recommendation_policy_name
        seen["policy_selection_metadata"] = policy_selection_metadata
        return None

    monkeypatch.setattr(
        recommendations_service,
        "inject_live_request",
        fake_inject_live_request,
    )
    monkeypatch.setenv("RECOMMENDATION_POLICY_NAME", "weighted_score")
    request = ExternalChargingRequest.model_validate(
        external_payload(preference_mode="Cheapest")
    )

    recommendations_service.generate_recommendations(request)

    assert seen["recommendation_policy_name"] == "weighted_score"
    assert seen["policy_selection_metadata"]["policy_source"] == (
        "recommendation_policy_name"
    )
    assert seen["policy_selection_metadata"]["policy_override_used"] is True
    assert request.preference_mode == "cheapest"


def test_forced_policy_env_var_has_top_precedence(monkeypatch) -> None:
    clear_recommendation_policy_env(monkeypatch)
    recommendations_service = import_recommendations_service(monkeypatch)
    seen = {}

    def fake_inject_live_request(request, *, recommendation_policy_name=None, policy_selection_metadata=None):
        seen["recommendation_policy_name"] = recommendation_policy_name
        seen["policy_selection_metadata"] = policy_selection_metadata
        return None

    monkeypatch.setattr(recommendations_service, "inject_live_request", fake_inject_live_request)
    monkeypatch.setenv("RECOMMENDATION_POLICY_NAME", "closest")
    monkeypatch.setenv("FORCE_RECOMMENDATION_POLICY", "rl_maskable_ppo_feeder")
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode="Fastest"))

    recommendations_service.generate_recommendations(request)

    assert seen["recommendation_policy_name"] == "rl_maskable_ppo_feeder"
    assert seen["policy_selection_metadata"]["policy_source"] == "force_recommendation_policy"


def test_explicit_policy_override_still_wins_over_app_preference(monkeypatch) -> None:
    clear_recommendation_policy_env(monkeypatch)
    recommendations_service = import_recommendations_service(monkeypatch)
    seen = {}

    def fake_inject_live_request(request, *, recommendation_policy_name=None, policy_selection_metadata=None):
        seen["recommendation_policy_name"] = recommendation_policy_name
        seen["policy_selection_metadata"] = policy_selection_metadata
        return None

    monkeypatch.setattr(recommendations_service, "inject_live_request", fake_inject_live_request)
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode="Closest"))

    recommendations_service.generate_recommendations(
        request,
        recommendation_policy_name="weighted_score",
    )

    assert seen["recommendation_policy_name"] == "weighted_score"


def test_enabled_safety_maps_preference_policy_to_hybrid() -> None:
    selection = select_recommendation_policy(
        preference_mode="cheapest",
        config=RecommendationConfig(
            policy_name="",
            rl_safety_filter_enabled=True,
        ),
    )

    assert selection.requested_policy_name == "cheapest"
    assert selection.effective_policy_name == "rl_safety_cheapest"
    assert selection.preference_mode == "cheapest"


def test_explicit_hybrid_policy_self_enables_when_global_flag_is_false() -> None:
    selection = select_recommendation_policy(
        preference_mode="closest",
        explicit_policy_name="rl_safety_preference",
        config=RecommendationConfig(policy_name="", rl_safety_filter_enabled=False),
    )

    assert selection.effective_policy_name == "rl_safety_preference"
    assert selection.rl_safety_filter_enabled is True


def test_disabled_safety_keeps_normal_preference_policy() -> None:
    selection = select_recommendation_policy(
        preference_mode="fastest",
        config=RecommendationConfig(policy_name="", rl_safety_filter_enabled=False),
    )

    assert selection.effective_policy_name == "fastest"


@pytest.mark.parametrize(
    ("app_value", "policy_name"),
    [
        ("Cheapest", "cheapest"),
        ("Fastest", "fastest"),
        ("Closest", "closest"),
        ("cheapest", "cheapest"),
        ("fastest", "fastest"),
        ("closest", "closest"),
    ],
)
def test_mobile_schema_accepts_visible_app_mode_values(monkeypatch, app_value: str, policy_name: str) -> None:
    fake_user_module = types.ModuleType("app.models.user")
    fake_user_module.User = object
    monkeypatch.setitem(sys.modules, "app.models.user", fake_user_module)
    mobile_schema = importlib.import_module("app.schemas.mobile_recommendations")

    request = mobile_schema.MobileRecommendationRequest.model_validate(
        {
            "latitude": 56.462,
            "longitude": -2.9707,
            "battery_level": 45,
            "target_battery_level": 80,
            "battery_kwh": 60,
            "requested_energy_kwh": 21,
            "preference_mode": app_value,
            "connector_type": "DC",
            "latest_finish_minutes_from_now": 120,
            "zone_id": "zone_central_waterfront",
        }
    )

    assert request.preference_mode == policy_name


def test_current_mobile_payload_values_still_validate(monkeypatch) -> None:
    fake_user_module = types.ModuleType("app.models.user")
    fake_user_module.User = object
    monkeypatch.setitem(sys.modules, "app.models.user", fake_user_module)
    mobile_schema = importlib.import_module("app.schemas.mobile_recommendations")

    request = mobile_schema.MobileRecommendationRequest.model_validate(
        {
            "latitude": 56.462,
            "longitude": -2.9707,
            "battery_level": 45,
            "target_battery_level": 80,
            "battery_kwh": 60,
            "requested_energy_kwh": 21,
            "preference_mode": "cheapest",
            "connector_type": "rapid",
            "latest_finish_minutes_from_now": 120,
            "zone_id": "zone_central_waterfront",
            "metadata": {"channel": "mobile-app"},
        }
    )

    assert request.preference_mode == "cheapest"
    assert request.connector_type == "rapid"
