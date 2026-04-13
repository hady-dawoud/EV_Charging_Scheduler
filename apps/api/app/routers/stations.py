from fastapi import APIRouter

from app.schemas import StationsResponse
from app.services.stations_service import list_stations

router = APIRouter(tags=["stations"])


@router.get("/stations", response_model=StationsResponse)
def get_stations():
    return {"stations": list_stations()}