from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_location: str | None = Field(default=None, min_length=2, max_length=100)
    max_price_per_kwh: float | None = Field(default=None, ge=0)
    available_only: bool = True


class Recommendation(BaseModel):
    station_id: int
    station_name: str
    location: str
    available_ports: int
    price_per_kwh: float
    score: float
    reason: str


class RecommendationsResponse(BaseModel):
    recommendations: list[Recommendation]