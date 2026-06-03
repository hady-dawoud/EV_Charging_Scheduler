from pydantic import BaseModel, ConfigDict, Field


class UserVehicleRead(BaseModel):
    id: str
    make: str
    model: str
    battery_capacity_kwh: float
    current_soc: float
    range_km: float


class UserVehicleUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: str = Field(..., min_length=1, max_length=120)
    model: str = Field(..., min_length=1, max_length=120)
    battery_capacity_kwh: float = Field(..., gt=0, le=250)
    current_soc: float = Field(..., ge=0, le=100)
    range_km: float = Field(..., ge=0, le=2000)
