from app.mock_data import stations


def list_stations():
    return stations


def get_station_by_id(station_id: int):
    for station in stations:
        if station["id"] == station_id:
            return station
    return None