from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ev_core.contracts.requests import ExternalChargingRequest

from app.models.user import User
from app.schemas.mobile_recommendations import MobileRecommendationRequest
from app.schemas.recommendations import RecommendationsResponse
from app.services.recommendations_service import generate_recommendations


def _build_client_request_id(current_user: User) -> str:
    suffix = uuid.uuid4().hex[:12]
    return f"mobile_{current_user.id}_{suffix}"


def _build_metadata(
    *,
    current_user: User,
    request: MobileRecommendationRequest,
) -> dict[str, Any]:
    metadata = dict(request.metadata)
    metadata.update(
        {
            "source": "mobile_app",
            "user_id": str(current_user.id),
        }
    )
    return metadata


def generate_mobile_recommendations(
    request: MobileRecommendationRequest,
    *,
    current_user: User,
) -> RecommendationsResponse:
    now = datetime.now(timezone.utc)
    latest_finish = now + timedelta(
        minutes=request.latest_finish_minutes_from_now,
    )

    runtime_request = ExternalChargingRequest(
        client_request_id=request.client_request_id or _build_client_request_id(current_user),
        request_timestamp=now,
        current_latitude=request.latitude,
        current_longitude=request.longitude,
        current_soc=request.battery_level,
        target_soc=request.target_battery_level,
        battery_kwh=request.battery_kwh,
        vehicle_profile_id=request.vehicle_profile_id,
        vehicle_max_ac_kw=request.vehicle_max_ac_kw,
        vehicle_max_dc_kw=request.vehicle_max_dc_kw,
        requested_energy_kwh=request.requested_energy_kwh,
        preference_mode=request.preference_mode,
        charger_type=request.connector_type,
        latest_finish_ts=latest_finish,
        source_type="external_live",
        zone_id=request.zone_id,
        metadata=_build_metadata(
            current_user=current_user,
            request=request,
        ),
    )

    return generate_recommendations(runtime_request)
