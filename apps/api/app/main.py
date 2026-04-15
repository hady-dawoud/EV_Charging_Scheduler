from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.recommendations import router as recommendations_router
from app.routers.stations import router as stations_router
from app.routers.system import router as system_router

app = FastAPI(title="EV Smart Charging API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://192.168.1.140:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(stations_router)
app.include_router(recommendations_router)