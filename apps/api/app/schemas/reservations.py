from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = Field(default=None, max_length=255)
    request_id: str | None = Field(default=None, max_length=255)
    station_id: str = Field(..., min_length=2, max_length=255)
    recommendation_rank: int | None = Field(default=None, ge=1)
    reserved_start_at: datetime
    reserved_until: datetime | None = None


class ReservationRead(BaseModel):
    reservation_id: str
    status: str
    station_id: str
    station_name: str
    client_request_id: str | None = None
    request_id: str | None = None
    recommendation_rank: int | None = None
    reserved_start_at: datetime
    reserved_until: datetime
    cancelled_at: datetime | None = None
    created_at: datetime


class ReservationsResponse(BaseModel):
    reservations: list[ReservationRead]


class ReservationCancelResponse(BaseModel):
    reservation_id: str
    status: str
