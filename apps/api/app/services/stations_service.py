from app.mock_data import stations
from app.schemas.stations import Station, StationCreate, StationUpdate


def list_stations(
    location: str | None = None,
    available_only: bool = False,
) -> list[Station]:
    results = [Station(**station) for station in stations]

    if location:
        results = [
            station
            for station in results
            if station.location.lower() == location.lower()
        ]

    if available_only:
        results = [
            station
            for station in results
            if station.available_ports > 0
        ]

    return results


def get_station_by_id(station_id: int) -> Station | None:
    for station in stations:
        if station["id"] == station_id:
            return Station(**station)
    return None


def create_station(station_in: StationCreate) -> Station:
    next_id = max((station["id"] for station in stations), default=0) + 1

    new_station = Station(
        id=next_id,
        name=station_in.name,
        location=station_in.location,
        available_ports=station_in.available_ports,
        price_per_kwh=station_in.price_per_kwh,
    )

    stations.append(new_station.model_dump())
    return new_station


def update_station(station_id: int, station_in: StationUpdate) -> Station | None:
    for index, station in enumerate(stations):
        if station["id"] == station_id:
            updated_station = Station(
                id=station_id,
                name=station_in.name,
                location=station_in.location,
                available_ports=station_in.available_ports,
                price_per_kwh=station_in.price_per_kwh,
            )
            stations[index] = updated_station.model_dump()
            return updated_station

    return None


def delete_station(station_id: int) -> bool:
    for index, station in enumerate(stations):
        if station["id"] == station_id:
            del stations[index]
            return True

    return False