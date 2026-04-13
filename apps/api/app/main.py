from fastapi import FastAPI
from app.routers.stations import router as stations_router


app = FastAPI(title="EV Smart Charging API")


@app.get("/")
def root():
    return {"message": "EV Smart Charging API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(stations_router)