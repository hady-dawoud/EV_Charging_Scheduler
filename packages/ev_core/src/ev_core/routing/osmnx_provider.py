"""Optional OSMnx-backed routing provider."""

from __future__ import annotations

from importlib import import_module
import math
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

    def is_available(self) -> bool:
        if not self.graph_path.exists():
            return False
        try:
            self._import_backends()
        except ModuleNotFoundError:
            return False
        return True

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
            origin_node = self._nearest_node_id(graph, osmnx, longitude=origin_longitude, latitude=origin_latitude)
            destination_node = self._nearest_node_id(graph, osmnx, longitude=float(station.longitude), latitude=float(station.latitude))
            if hasattr(graph, "nodes"):
                route_nodes = networkx.shortest_path(graph, origin_node, destination_node, weight=self._edge_weight_resolver("length"))
                distance_m = self._path_weight(graph, route_nodes, "length")
                distance_km = distance_m / 1000.0
                try:
                    duration_minutes = self._path_weight(graph, route_nodes, "travel_time") / 60.0
                    duration_source = "graph_travel_time"
                except Exception:
                    duration_minutes = (distance_km / self.speed_kph) * 60.0
                    duration_source = "speed_kph_fallback"
            else:
                route_nodes = networkx.shortest_path(graph, origin_node, destination_node, weight="length")
                distance_km = float(networkx.path_weight(graph, route_nodes, weight="length")) / 1000.0
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

    def _nearest_node_id(self, graph: Any, osmnx: Any, *, longitude: float, latitude: float) -> Any:
        if not hasattr(graph, "nodes"):
            return osmnx.distance.nearest_nodes(graph, longitude, latitude)
        nearest_node: Any | None = None
        nearest_distance = float("inf")
        for node_id, attrs in graph.nodes(data=True):
            node_x = float(attrs["x"])
            node_y = float(attrs["y"])
            distance = math.hypot((longitude - node_x) * 111.0 * 0.56, (latitude - node_y) * 111.0)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_node = node_id
        if nearest_node is None:
            raise RuntimeError("graph_contains_no_nodes")
        return nearest_node

    def _edge_weight_resolver(self, weight_name: str):
        def _resolver(u: Any, v: Any, attrs: Any) -> float:
            return self._edge_weight_from_attrs(attrs, weight_name)

        return _resolver

    def _path_weight(self, graph: Any, route_nodes: list[Any], weight_name: str) -> float:
        total = 0.0
        for origin, destination in zip(route_nodes, route_nodes[1:]):
            edge_data = graph.get_edge_data(origin, destination)
            if edge_data is None:
                raise KeyError(f"missing edge {origin}->{destination}")
            total += self._edge_weight_from_attrs(edge_data, weight_name)
        return total

    def _edge_weight_from_attrs(self, attrs: Any, weight_name: str) -> float:
        if isinstance(attrs, dict) and weight_name in attrs:
            return float(attrs[weight_name])
        if isinstance(attrs, dict):
            candidates = []
            for value in attrs.values():
                if isinstance(value, dict) and weight_name in value:
                    candidates.append(float(value[weight_name]))
            if candidates:
                return min(candidates)
        raise KeyError(weight_name)


__all__ = ["OSMnxRoutingProvider"]
