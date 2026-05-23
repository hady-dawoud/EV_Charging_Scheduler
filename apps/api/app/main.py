from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.auth import router as auth_router
from app.routers.charger_events import router as charger_events_router
from app.routers.mobile_recommendations import router as mobile_recommendations_router
from app.routers.charging_sessions import router as charging_sessions_router
from app.routers.recommendations import router as recommendations_router
from app.routers.reservations import router as reservations_router
from app.routers.stations import router as stations_router
from app.routers.system import router as system_router

settings = get_settings()

app = FastAPI(
    title="EV Smart Charging API",
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(mobile_recommendations_router)
app.include_router(charging_sessions_router)
app.include_router(charger_events_router)
app.include_router(reservations_router)
app.include_router(stations_router)
app.include_router(recommendations_router)
