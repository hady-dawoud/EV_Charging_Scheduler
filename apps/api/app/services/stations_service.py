from app.mock_data import stations


def list_stations(location: str | None = None):
    results = stations

    if location:
        results = [
            station
            for station in results
            if station["location"].lower() == location.lower()
        ]

    return results


def get_station_by_id(station_id: int):
    for station in stations:
        if station["id"] == station_id:
            return station
    return None