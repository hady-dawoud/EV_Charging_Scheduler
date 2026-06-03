from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.recommender.policy_registry import PolicyRegistry


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
    assert PolicyRegistry().get(request.preference_mode).name == policy_name


def test_external_request_invalid_preference_mode_fails_clearly() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExternalChargingRequest.model_validate(external_payload(preference_mode="Greenest"))

    message = str(exc_info.value)
    assert "preference_mode" in message
    assert "closest" in message
    assert "cheapest" in message
    assert "fastest" in message


def test_recommendations_service_maps_app_preference_to_recommender_policy(monkeypatch) -> None:
    recommendations_service = importlib.import_module("app.services.recommendations_service")
    seen = {}

    def fake_inject_live_request(request, *, recommendation_policy_name=None):
        seen["request"] = request
        seen["recommendation_policy_name"] = recommendation_policy_name
        return None

    monkeypatch.setattr(recommendations_service, "inject_live_request", fake_inject_live_request)
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode="Cheapest"))

    recommendations_service.generate_recommendations(request)

    assert seen["request"] is request
    assert seen["recommendation_policy_name"] == "cheapest"


def test_explicit_policy_override_still_wins_over_app_preference(monkeypatch) -> None:
    recommendations_service = importlib.import_module("app.services.recommendations_service")
    seen = {}

    def fake_inject_live_request(request, *, recommendation_policy_name=None):
        seen["recommendation_policy_name"] = recommendation_policy_name
        return None

    monkeypatch.setattr(recommendations_service, "inject_live_request", fake_inject_live_request)
    request = ExternalChargingRequest.model_validate(external_payload(preference_mode="Closest"))

    recommendations_service.generate_recommendations(
        request,
        recommendation_policy_name="weighted_score",
    )

    assert seen["recommendation_policy_name"] == "weighted_score"


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
