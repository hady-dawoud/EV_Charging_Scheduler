"""Shared schema placeholders for future backend and EV-core integration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TimeWindow(BaseModel):
    """Represents a bounded time window on the internal 15-minute time base."""

    start: datetime
    end: datetime
    resolution_minutes: int = Field(default=15, description="Internal time-step size.")


class ChargingRequest(BaseModel):
    """Minimal charging-request contract for simulation and recommendation flows."""

    request_id: str
    vehicle_id: str
    station_id: Optional[str] = None
    arrival_at: datetime
    departure_by: datetime
    requested_energy_kwh: float
    requested_max_power_kw: Optional[float] = None


class StationSnapshot(BaseModel):
    """Station state snapshot aligned to a single 15-minute interval."""

    station_id: str
    observed_at: datetime
    total_connectors: int
    available_connectors: int
    queued_requests: int = 0


class RecommendationCandidate(BaseModel):
    """Placeholder candidate payload for future ranking outputs."""

    station_id: str
    score: Optional[float] = None
    expected_wait_minutes: Optional[int] = None
    note: Optional[str] = None
