from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.stations import (
    Station,
    StationCreate,
    StationUpdate,
    StationsResponse,
)
from app.services.stations_service import (
    create_station,
    delete_station,
    get_station_by_id,
    list_stations,
    update_station,
)

router = APIRouter(tags=["stations"])


@router.get("/stations", response_model=StationsResponse)
def get_stations(
    location: str | None = Query(default=None),
    available_only: bool = Query(default=False),
):
    return {
        "stations": list_stations(
            location=location,
            available_only=available_only,
        )
    }


@router.get("/stations/{station_id}", response_model=Station)
def get_station(station_id: int):
    station = get_station_by_id(station_id)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station


@router.post("/stations", response_model=Station, status_code=status.HTTP_201_CREATED)
def add_station(station_in: StationCreate):
    return create_station(station_in)


@router.put("/stations/{station_id}", response_model=Station)
def edit_station(station_id: int, station_in: StationUpdate):
    station = update_station(station_id, station_in)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station


@router.delete("/stations/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_station(station_id: int):
    deleted = delete_station(station_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Station not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)