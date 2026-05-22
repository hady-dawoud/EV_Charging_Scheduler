from pydantic import BaseModel, ConfigDict, Field


class StationBase(BaseModel):
    station_name: str = Field(..., min_length=2, max_length=255)
    postcode: str | None = Field(default=None, max_length=50)
    latitude: float
    longitude: float
    zone_id: str | None = Field(default=None, max_length=255)
    transformer_id: str | None = Field(default=None, max_length=255)
    cp_count_total: int = Field(default=0, ge=0)
    connector_mix_total: str | None = Field(default=None, max_length=255)
    station_max_power_kw_proxy: float | None = Field(default=None, ge=0)
    station_capacity_kw_assumed: float | None = Field(default=None, ge=0)
    is_public: bool = True
    is_fleet_only: bool = False
    requires_membership: bool = False
    exclude_from_recommendations: bool = False
    access_notes: str | None = None
    location_source: str | None = Field(default=None, max_length=255)
    location_confidence: str | None = Field(default=None, max_length=50)
    needs_followup: bool = False
    sessions_total: int = Field(default=0, ge=0)
    energy_total_kwh: float = Field(default=0.0, ge=0)


class Station(StationBase):
    model_config = ConfigDict(from_attributes=True)

    station_id: str


class StationCreate(StationBase):
    model_config = ConfigDict(extra="forbid")

    station_id: str = Field(..., min_length=2, max_length=255)


class StationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    station_name: str | None = Field(default=None, min_length=2, max_length=255)
    postcode: str | None = Field(default=None, max_length=50)
    latitude: float | None = None
    longitude: float | None = None
    zone_id: str | None = Field(default=None, max_length=255)
    transformer_id: str | None = Field(default=None, max_length=255)
    cp_count_total: int | None = Field(default=None, ge=0)
    connector_mix_total: str | None = Field(default=None, max_length=255)
    station_max_power_kw_proxy: float | None = Field(default=None, ge=0)
    station_capacity_kw_assumed: float | None = Field(default=None, ge=0)
    is_public: bool | None = None
    is_fleet_only: bool | None = None
    requires_membership: bool | None = None
    exclude_from_recommendations: bool | None = None
    access_notes: str | None = None
    location_source: str | None = Field(default=None, max_length=255)
    location_confidence: str | None = Field(default=None, max_length=50)
    needs_followup: bool | None = None
    sessions_total: int | None = Field(default=None, ge=0)
    energy_total_kwh: float | None = Field(default=None, ge=0)


class StationsResponse(BaseModel):
    stations: list[Station]
