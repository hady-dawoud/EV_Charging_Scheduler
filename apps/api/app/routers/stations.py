from fastapi import APIRouter, HTTPException

from app.schemas.stations import Station, StationsResponse
from app.services.stations_service import get_station_by_id, list_stations

router = APIRouter(tags=["stations"])


@router.get("/stations", response_model=StationsResponse)
def get_stations():
    return {"stations": list_stations()}


@router.get("/stations/{station_id}", response_model=Station)
def get_station(station_id: int):
    station = get_station_by_id(station_id)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station