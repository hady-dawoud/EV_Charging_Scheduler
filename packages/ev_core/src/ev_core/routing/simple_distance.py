"""Simple coordinate-based routing provider used by default."""

from __future__ import annotations

from ev_core.routing.providers import RouteEstimate


def simple_distance_km(
    lat_a: float | None,
    lon_a: float | None,
    lat_b: float,
    lon_b: float,
    *,
    lat_scale_km_per_degree: float = 111.0,
    lon_scale_km_per_degree: float = 111.0 * 0.56,
    missing_coordinate_distance_km: float = 3.0,
) -> float:
    """Preserve the existing simple lat/lon distance approximation."""

    if lat_a is None or lon_a is None:
        return float(missing_coordinate_distance_km)
    return float(
        (((lat_a - lat_b) * lat_scale_km_per_degree) ** 2 + ((lon_a - lon_b) * lon_scale_km_per_degree) ** 2) ** 0.5
    )


class SimpleDistanceRoutingProvider:
    """Default provider that preserves the existing Dundee simple-distance behavior."""

    name = "simple_distance"

    def __init__(
        self,
        *,
        lat_scale_km_per_degree: float = 111.0,
        lon_scale_km_per_degree: float = 111.0 * 0.56,
        same_zone_fallback_km: float = 0.5,
        different_zone_fallback_km: float = 3.0,
    ) -> None:
        self.lat_scale_km_per_degree = float(lat_scale_km_per_degree)
        self.lon_scale_km_per_degree = float(lon_scale_km_per_degree)
        self.same_zone_fallback_km = float(same_zone_fallback_km)
        self.different_zone_fallback_km = float(different_zone_fallback_km)

    def estimate_route(self, request, station) -> RouteEstimate:
        """Estimate a simple point-to-station route distance."""

        latitude = getattr(request, "current_latitude", None)
        longitude = getattr(request, "current_longitude", None)
        if latitude is None or longitude is None:
            same_zone = getattr(request, "zone_id", None) == getattr(station, "zone_id", None)
            distance_km = self.same_zone_fallback_km if same_zone else self.different_zone_fallback_km
            return RouteEstimate(
                distance_km=distance_km,
                duration_minutes=None,
                provider=self.name,
                metadata={
                    "mode": "zone_fallback",
                    "same_zone": same_zone,
                },
            )
        return RouteEstimate(
            distance_km=simple_distance_km(
                latitude,
                longitude,
                float(station.latitude),
                float(station.longitude),
                lat_scale_km_per_degree=self.lat_scale_km_per_degree,
                lon_scale_km_per_degree=self.lon_scale_km_per_degree,
                missing_coordinate_distance_km=self.different_zone_fallback_km,
            ),
            duration_minutes=None,
            provider=self.name,
            metadata={
                "mode": "coordinate_distance",
                "lat_scale_km_per_degree": self.lat_scale_km_per_degree,
                "lon_scale_km_per_degree": self.lon_scale_km_per_degree,
            },
        )


__all__ = ["SimpleDistanceRoutingProvider", "simple_distance_km"]
