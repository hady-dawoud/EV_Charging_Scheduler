"""Standalone request contracts for the EV-side simulator runtime.

These models are intentionally independent from anything under ``apps/**`` so
future mobile or backend integration can bind to them without coupling the
simulator core to the existing prototype layers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PreferenceMode = Literal["closest", "cheapest", "fastest"]
SourceType = Literal["replay_background", "synthetic_background", "external_live"]
MAX_BATTERY_KWH = 250.0
MAX_VEHICLE_AC_KW = 50.0
MAX_VEHICLE_DC_KW = 500.0
SUPPORTED_CHARGER_TYPES = {"any", "ac", "dc", "rapid", "ultrarapid", "ultra_rapid", "ultra rapid"}


class ExternalChargingRequest(BaseModel):
    """Integration-safe charging request for replay or live-style injection."""

    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(description="Client-side identifier propagated through future integrations.")
    request_timestamp: datetime = Field(description="Timestamp when the request is issued to the simulator.")
    current_latitude: Optional[float] = Field(default=None, description="Current user latitude when known.")
    current_longitude: Optional[float] = Field(default=None, description="Current user longitude when known.")
    target_soc: Optional[float] = Field(default=None, description="Requested target state of charge as a percentage.")
    current_soc: Optional[float] = Field(default=None, description="Current state of charge as a percentage.")
    battery_kwh: Optional[float] = Field(default=None, description="Vehicle battery capacity used for energy inference.")
    vehicle_profile_id: Optional[str] = Field(default=None, description="Optional vehicle profile identifier for future catalog lookup.")
    vehicle_max_ac_kw: Optional[float] = Field(default=None, description="Optional vehicle AC charging power limit.")
    vehicle_max_dc_kw: Optional[float] = Field(default=None, description="Optional vehicle DC/Rapid charging power limit.")
    requested_energy_kwh: Optional[float] = Field(default=None, description="Explicit requested energy when already known.")
    preference_mode: PreferenceMode = Field(default="fastest", description="Primary user preference heuristic.")
    charger_type: str = Field(default="Any", description="Requested charger class, such as ac, dc, rapid, or Any.")
    latest_finish_ts: datetime = Field(description="Latest acceptable finish timestamp for the charging request.")
    source_type: SourceType = Field(default="external_live", description="Origin of the request inside the simulator.")
    request_id: Optional[str] = Field(default=None, description="Optional runtime request identifier when already assigned.")
    zone_id: Optional[str] = Field(default=None, description="Optional zone hint when location is unavailable.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional standalone request metadata.")

    @field_validator("request_timestamp", "latest_finish_ts")
    @classmethod
    def normalize_timezone(cls, value: datetime) -> datetime:
        """Convert timezone-aware timestamps to naive UTC for internal runtime use."""

        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @field_validator("current_soc", "target_soc")
    @classmethod
    def validate_soc_range(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not 0.0 <= value <= 100.0:
            raise ValueError("SOC values must be between 0 and 100.")
        return value

    @field_validator("battery_kwh")
    @classmethod
    def validate_battery_capacity(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0.0:
            raise ValueError("battery_kwh must be greater than 0.")
        if value > MAX_BATTERY_KWH:
            raise ValueError(f"battery_kwh must be less than or equal to {MAX_BATTERY_KWH}.")
        return value

    @field_validator("requested_energy_kwh")
    @classmethod
    def validate_requested_energy_positive(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0.0:
            raise ValueError("requested_energy_kwh must be greater than 0.")
        return value

    @field_validator("vehicle_max_ac_kw")
    @classmethod
    def validate_vehicle_max_ac_kw(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0.0:
            raise ValueError("vehicle_max_ac_kw must be greater than 0.")
        if value > MAX_VEHICLE_AC_KW:
            raise ValueError(f"vehicle_max_ac_kw must be less than or equal to {MAX_VEHICLE_AC_KW}.")
        return value

    @field_validator("vehicle_max_dc_kw")
    @classmethod
    def validate_vehicle_max_dc_kw(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0.0:
            raise ValueError("vehicle_max_dc_kw must be greater than 0.")
        if value > MAX_VEHICLE_DC_KW:
            raise ValueError(f"vehicle_max_dc_kw must be less than or equal to {MAX_VEHICLE_DC_KW}.")
        return value

    @field_validator("current_latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not -90.0 <= value <= 90.0:
            raise ValueError("current_latitude must be between -90 and 90.")
        return value

    @field_validator("current_longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not -180.0 <= value <= 180.0:
            raise ValueError("current_longitude must be between -180 and 180.")
        return value

    @field_validator("charger_type")
    @classmethod
    def validate_charger_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in SUPPORTED_CHARGER_TYPES:
            raise ValueError("charger_type must be one of Any, AC, DC, Rapid, UltraRapid, or ultra_rapid.")
        return value

    @model_validator(mode="after")
    def validate_domain_consistency(self) -> "ExternalChargingRequest":
        """Infer requested energy and validate live request domain consistency."""

        if self.target_soc is not None and self.current_soc is not None and self.target_soc <= self.current_soc:
            raise ValueError("target_soc must be greater than current_soc.")
        if self.requested_energy_kwh is None:
            if self.target_soc is not None and self.current_soc is not None and self.battery_kwh is not None:
                soc_gap = self.target_soc - self.current_soc
                self.requested_energy_kwh = round((soc_gap / 100.0) * self.battery_kwh, 3)
        if self.requested_energy_kwh is None:
            self.requested_energy_kwh = 20.0
        if self.requested_energy_kwh <= 0.0:
            raise ValueError("requested_energy_kwh must be greater than 0.")
        if self.battery_kwh is not None and self.requested_energy_kwh > self.battery_kwh:
            raise ValueError("requested_energy_kwh must be less than or equal to battery_kwh.")
        if self.target_soc is not None and self.current_soc is not None and self.battery_kwh is not None:
            expected_energy = ((self.target_soc - self.current_soc) / 100.0) * self.battery_kwh
            mismatch = abs(self.requested_energy_kwh - expected_energy)
            relative_mismatch = mismatch / max(expected_energy, 1.0)
            if mismatch > 0.5 and relative_mismatch > 0.05:
                raise ValueError("requested_energy_kwh is inconsistent with SOC-derived energy.")
        if self.latest_finish_ts <= self.request_timestamp:
            raise ValueError("latest_finish_ts must be after request_timestamp.")
        return self


__all__ = [
    "ExternalChargingRequest",
    "PreferenceMode",
    "SourceType",
]
