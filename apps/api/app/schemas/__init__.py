from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "ActiveChargingSessionResponse": "charging_sessions",
    "AuthResponse": "auth",
    "ChargingSessionCompleteRequest": "charging_sessions",
    "ChargingSessionCreate": "charging_sessions",
    "ChargingSessionRead": "charging_sessions",
    "ChargingSessionsResponse": "charging_sessions",
    "ErrorResponse": "errors",
    "LoginRequest": "auth",
    "LogoutRequest": "auth",
    "LogoutResponse": "auth",
    "MobileRecommendationRequest": "mobile_recommendations",
    "RecommendationRequest": "recommendations",
    "RecommendationsResponse": "recommendations",
    "RefreshTokenRequest": "auth",
    "RefreshTokenResponse": "auth",
    "RegisterRequest": "auth",
    "ReservationCancelResponse": "reservations",
    "ReservationCreate": "reservations",
    "ReservationRead": "reservations",
    "ReservationsResponse": "reservations",
    "Station": "stations",
    "StationCreate": "stations",
    "StationUpdate": "stations",
    "StationsResponse": "stations",
    "TokenPair": "auth",
    "UserRead": "auth",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module 'app.schemas' has no attribute {name!r}")
    module = import_module(f"app.schemas.{_EXPORT_MODULES[name]}")
    value = getattr(module, name)
    globals()[name] = value
    return value
