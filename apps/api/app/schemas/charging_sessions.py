from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChargingSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    station_id: str = Field(..., min_length=2, max_length=255)
    reservation_id: str | None = None
    client_request_id: str | None = Field(default=None, max_length=255)
    request_id: str | None = Field(default=None, max_length=255)
    started_at: datetime | None = None
    connector_type: str | None = Field(default=None, max_length=100)
    charger_power_kw: float | None = Field(default=None, ge=0)


class ChargingSessionCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ended_at: datetime | None = None
    energy_kwh: float = Field(..., ge=0)
    cost_total: float | None = Field(default=None, ge=0)


class ChargingSessionRead(BaseModel):
    session_id: str
    status: str
    station_id: str
    station_name: str
    reservation_id: str | None = None
    client_request_id: str | None = None
    request_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    energy_kwh: float
    cost_total: float | None = None
    connector_type: str | None = None
    charger_power_kw: float | None = None
    created_at: datetime


class ChargingSessionsResponse(BaseModel):
    sessions: list[ChargingSessionRead]


class ActiveChargingSessionResponse(BaseModel):
    session: ChargingSessionRead | None
