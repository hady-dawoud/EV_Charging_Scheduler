from pydantic import BaseModel
from typing import List


class Station(BaseModel):
    id: int
    name: str
    location: str
    available_ports: int
    price_per_kwh: float


class StationsResponse(BaseModel):
    stations: List[Station]