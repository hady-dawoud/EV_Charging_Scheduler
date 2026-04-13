from pydantic import BaseModel


class Station(BaseModel):
    id: int
    name: str
    location: str
    available_ports: int
    price_per_kwh: float


class StationsResponse(BaseModel):
    stations: list[Station]