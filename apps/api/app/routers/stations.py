from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api_responses import not_found_response
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

router = APIRouter(
    prefix="/stations",
    tags=["stations"],
)


@router.get(
    "",
    response_model=StationsResponse,
    summary="List stations",
    description="Return all stations, with optional filtering by location and availability.",
    response_description="A list of stations.",
)
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


@router.get(
    "/{station_id}",
    response_model=Station,
    summary="Get station by ID",
    description="Return a single station using its numeric identifier.",
    response_description="The requested station.",
    responses=not_found_response("Station"),
)
def get_station(station_id: int):
    station = get_station_by_id(station_id)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station


@router.post(
    "",
    response_model=Station,
    status_code=status.HTTP_201_CREATED,
    summary="Create station",
    description="Create a new station in the in-memory mock store.",
    response_description="The newly created station.",
)
def add_station(station_in: StationCreate):
    return create_station(station_in)


@router.put(
    "/{station_id}",
    response_model=Station,
    summary="Update station",
    description="Replace an existing station by ID.",
    response_description="The updated station.",
    responses=not_found_response("Station"),
)
def edit_station(station_id: int, station_in: StationUpdate):
    station = update_station(station_id, station_in)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station


@router.delete(
    "/{station_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete station",
    description="Delete a station by ID.",
    response_description="Station deleted successfully.",
    responses=not_found_response("Station"),
)
def remove_station(station_id: int):
    deleted = delete_station(station_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Station not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)