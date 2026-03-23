from fastapi import FastAPI
from app.mock_data import stations

app = FastAPI(title="EV Smart Charging API")


@app.get("/")
def root():
    return {"message": "EV Smart Charging API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stations")
def get_stations():
    return {"stations": stations}