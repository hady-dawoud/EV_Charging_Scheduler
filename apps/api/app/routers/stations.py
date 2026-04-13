from fastapi import APIRouter

from app.mock_data import stations
from app.schemas import StationsResponse

router = APIRouter(tags=["stations"])


@router.get("/stations", response_model=StationsResponse)
def get_stations():
    return {"stations": stations}