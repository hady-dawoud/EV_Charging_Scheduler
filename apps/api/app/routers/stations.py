from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api_responses import not_found_response
from app.db.session import get_db
from app.schemas.stations import (
    Station,
    StationCreate,
    StationUpdate,
    StationsResponse,
)
from app.services.stations_service import (
    StationAlreadyExistsError,
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
    description="Return persisted stations, with optional filtering by zone and availability.",
    response_description="A list of stations.",
)
def get_stations(
    zone_id: str | None = Query(default=None),
    available_only: bool = Query(default=False),
    public_only: bool = Query(default=True),
    include_excluded: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> StationsResponse:
    return StationsResponse(
        stations=list_stations(
            db,
            zone_id=zone_id,
            available_only=available_only,
            public_only=public_only,
            include_excluded=include_excluded,
        )
    )


@router.get(
    "/{station_id}",
    response_model=Station,
    summary="Get station by ID",
    description="Return a single station using its stable string station identifier.",
    response_description="The requested station.",
    responses=not_found_response("Station"),
)
def get_station(
    station_id: str,
    db: Session = Depends(get_db),
) -> Station:
    station = get_station_by_id(db, station_id)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station


@router.post(
    "",
    response_model=Station,
    status_code=status.HTTP_201_CREATED,
    summary="Create station",
    description="Create a new persisted station.",
    response_description="The newly created station.",
)
def add_station(
    station_in: StationCreate,
    db: Session = Depends(get_db),
) -> Station:
    try:
        return create_station(db, station_in)
    except StationAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put(
    "/{station_id}",
    response_model=Station,
    summary="Update station",
    description="Update an existing persisted station by string station ID.",
    response_description="The updated station.",
    responses=not_found_response("Station"),
)
def edit_station(
    station_id: str,
    station_in: StationUpdate,
    db: Session = Depends(get_db),
) -> Station:
    station = update_station(db, station_id, station_in)

    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    return station


@router.delete(
    "/{station_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete station",
    description="Delete a persisted station by string station ID.",
    response_description="Station deleted successfully.",
    responses=not_found_response("Station"),
)
def remove_station(
    station_id: str,
    db: Session = Depends(get_db),
) -> Response:
    deleted = delete_station(db, station_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Station not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
