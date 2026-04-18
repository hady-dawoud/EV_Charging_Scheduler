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

    @model_validator(mode="after")
    def infer_requested_energy(self) -> "ExternalChargingRequest":
        """Infer requested energy from SOC and battery capacity when not supplied."""

        if self.requested_energy_kwh is None:
            if self.target_soc is not None and self.current_soc is not None and self.battery_kwh is not None:
                soc_gap = max(self.target_soc - self.current_soc, 0.0)
                self.requested_energy_kwh = round((soc_gap / 100.0) * self.battery_kwh, 3)
        if self.requested_energy_kwh is None:
            self.requested_energy_kwh = 20.0
        return self


__all__ = [
    "ExternalChargingRequest",
    "PreferenceMode",
    "SourceType",
]
