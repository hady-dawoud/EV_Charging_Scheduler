from fastapi import FastAPI

from app.routers.stations import router as stations_router
from app.routers.system import router as system_router

app = FastAPI(title="EV Smart Charging API")

app.include_router(system_router)
app.include_router(stations_router)