"""Optional OSMnx-backed routing provider."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from ev_core.routing.providers import RouteEstimate, RoutingProvider
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider


class OSMnxRoutingProvider:
    """Optional offline road-routing provider backed by a cached GraphML file."""

    name = "osmnx"

    def __init__(
        self,
        *,
        graph_path: Path | str,
        fallback_provider: RoutingProvider | None = None,
        speed_kph: float = 30.0,
        fail_closed: bool = False,
    ) -> None:
        self.graph_path = Path(graph_path)
        self.fallback_provider = fallback_provider or SimpleDistanceRoutingProvider()
        self.speed_kph = max(float(speed_kph), 1.0)
        self.fail_closed = bool(fail_closed)
        self._graph: Any | None = None
        self._backends: tuple[Any, Any] | None = None

    def _import_backends(self) -> tuple[Any, Any]:
        """Load OSMnx and NetworkX lazily so the repo works without them installed."""

        if self._backends is None:
            self._backends = (import_module("osmnx"), import_module("networkx"))
        return self._backends

    def _load_graph(self) -> Any:
        """Load the cached GraphML file lazily."""

        if self._graph is None:
            if not self.graph_path.exists():
                raise FileNotFoundError(f"Graph file not found: {self.graph_path}")
            osmnx, _ = self._import_backends()
            self._graph = osmnx.load_graphml(self.graph_path)
        return self._graph

    def _failure(self, reason: str, error: Exception | None = None) -> RuntimeError:
        detail = str(error) if error is not None else reason
        return RuntimeError(f"OSMnx routing unavailable ({reason}) for graph '{self.graph_path}': {detail}")

    def _fallback_estimate(
        self,
        request: Any,
        station: Any,
        *,
        reason: str,
        error: Exception | None = None,
    ) -> RouteEstimate:
        if self.fail_closed:
            raise self._failure(reason, error)
        fallback = self.fallback_provider.estimate_route(request, station)
        metadata = dict(fallback.metadata or {})
        metadata.update(
            {
                "provider_requested": self.name,
                "graph_path": str(self.graph_path),
                "fallback_used": True,
                "fallback_reason": reason,
                "fallback_provider": fallback.provider,
            }
        )
        if error is not None:
            metadata["fallback_error"] = str(error)
        return RouteEstimate(
            distance_km=float(fallback.distance_km),
            duration_minutes=fallback.duration_minutes,
            provider=fallback.provider,
            metadata=metadata,
        )

    def estimate_route(self, request: Any, station: Any) -> RouteEstimate:
        """Estimate a shortest road path using a prebuilt OSMnx drive graph."""

        origin_latitude = getattr(request, "current_latitude", None)
        origin_longitude = getattr(request, "current_longitude", None)
        if origin_latitude is None or origin_longitude is None:
            return self._fallback_estimate(request, station, reason="request_coordinates_missing")

        try:
            graph = self._load_graph()
            osmnx, networkx = self._import_backends()
            origin_node = osmnx.distance.nearest_nodes(graph, origin_longitude, origin_latitude)
            destination_node = osmnx.distance.nearest_nodes(graph, float(station.longitude), float(station.latitude))
            route_nodes = networkx.shortest_path(graph, origin_node, destination_node, weight="length")
            distance_m = float(networkx.path_weight(graph, route_nodes, weight="length"))
            distance_km = distance_m / 1000.0
            try:
                duration_minutes = float(networkx.path_weight(graph, route_nodes, weight="travel_time")) / 60.0
                duration_source = "graph_travel_time"
            except Exception:
                duration_minutes = (distance_km / self.speed_kph) * 60.0
                duration_source = "speed_kph_fallback"
            return RouteEstimate(
                distance_km=distance_km,
                duration_minutes=duration_minutes,
                provider=self.name,
                metadata={
                    "origin_node": origin_node,
                    "destination_node": destination_node,
                    "graph_path": str(self.graph_path),
                    "fallback_used": False,
                    "provider_requested": self.name,
                    "route_nodes": list(route_nodes),
                    "duration_source": duration_source,
                },
            )
        except FileNotFoundError as error:
            return self._fallback_estimate(request, station, reason="graph_missing", error=error)
        except ModuleNotFoundError as error:
            return self._fallback_estimate(request, station, reason="backend_unavailable", error=error)
        except Exception as error:
            return self._fallback_estimate(request, station, reason="route_estimation_failed", error=error)


__all__ = ["OSMnxRoutingProvider"]
