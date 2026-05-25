from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ev_core.contracts.requests import normalize_preference_mode


class MobileRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    battery_level: float | None = Field(default=None, ge=0, le=100)
    target_battery_level: float | None = Field(default=None, ge=0, le=100)
    battery_kwh: float | None = Field(default=60.0, gt=0)
    vehicle_profile_id: str | None = Field(default=None, max_length=255)
    vehicle_max_ac_kw: float | None = Field(default=11.0, ge=0)
    vehicle_max_dc_kw: float | None = Field(default=150.0, ge=0)
    requested_energy_kwh: float | None = Field(default=None, ge=0)
    preference_mode: Literal["closest", "cheapest", "fastest"] = "fastest"
    connector_type: str = Field(default="Any", max_length=100)
    latest_finish_minutes_from_now: int = Field(default=90, ge=5, le=1440)
    zone_id: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("preference_mode", mode="before")
    @classmethod
    def normalize_preference_mode_value(cls, value: str) -> str:
        return normalize_preference_mode(value)
