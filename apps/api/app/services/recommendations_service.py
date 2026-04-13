from app.schemas.recommendations import Recommendation, RecommendationRequest
from app.services.stations_service import list_stations


def generate_recommendations(
    request: RecommendationRequest,
) -> list[Recommendation]:
    stations = list_stations(
        location=request.preferred_location,
        available_only=request.available_only,
    )

    recommendations: list[Recommendation] = []

    for station in stations:
        if (
            request.max_price_per_kwh is not None
            and station.price_per_kwh > request.max_price_per_kwh
        ):
            continue

        score = float((station.available_ports * 10) - station.price_per_kwh)

        recommendation = Recommendation(
            station_id=station.id,
            station_name=station.name,
            location=station.location,
            available_ports=station.available_ports,
            price_per_kwh=station.price_per_kwh,
            score=score,
            reason=(
                f"{station.available_ports} available ports, "
                f"{station.price_per_kwh} price per kWh"
            ),
        )
        recommendations.append(recommendation)

    recommendations.sort(key=lambda item: item.score, reverse=True)
    return recommendations