from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChargerSessionStartEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: str = Field(..., min_length=1)
    started_at: datetime | None = None
    connector_type: str | None = Field(default=None, max_length=100)
    charger_power_kw: float | None = Field(default=None, ge=0)


class ChargerSessionCompleteEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ended_at: datetime | None = None
    energy_kwh: float = Field(..., ge=0)
    cost_total: float | None = Field(default=None, ge=0)
