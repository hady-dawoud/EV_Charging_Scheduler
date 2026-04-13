from pydantic import BaseModel, ConfigDict, Field


class Station(BaseModel):
    id: int
    name: str
    location: str
    available_ports: int
    price_per_kwh: float


class StationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=100)
    available_ports: int = Field(..., ge=0)
    price_per_kwh: float = Field(..., ge=0)


class StationsResponse(BaseModel):
    stations: list[Station]