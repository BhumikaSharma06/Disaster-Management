"""Hazard-aware evacuation routing with an offline NetworkX fallback."""

from __future__ import annotations

import json
import math
from pathlib import Path

import networkx as nx

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
GRAPH_CACHE = CONFIG_DIR / "graph_cache"


def load_shelters() -> list[dict]:
    with (CONFIG_DIR / "pan_india_shelters.json").open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    shelters = payload.get("shelters")
    if not isinstance(shelters, list):
        raise ValueError("shelter catalogue must contain a shelters list")
    return shelters


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def nearest_shelters(latitude: float, longitude: float, limit: int = 5) -> list[dict]:
    ranked = []
    for shelter in load_shelters():
        item = dict(shelter)
        item["distance_km"] = round(
            haversine_km(latitude, longitude, shelter["latitude"], shelter["longitude"]),
            2,
        )
        item["source_name"] = "Pan-India prototype shelter catalogue"
        item["verification_status"] = "unverified"
        ranked.append(item)
    ranked.sort(key=lambda item: item["distance_km"])
    return ranked[:limit]


def build_fallback_graph(origin: tuple[float, float], destination: tuple[float, float]) -> nx.Graph:
    """Build a 5x5 local grid graph with haversine edge weights."""
    graph = nx.Graph()
    lat_min = min(origin[0], destination[0])
    lat_max = max(origin[0], destination[0])
    lon_min = min(origin[1], destination[1])
    lon_max = max(origin[1], destination[1])

    lat_span = max(lat_max - lat_min, 0.02)
    lon_span = max(lon_max - lon_min, 0.02)
    points: dict[tuple[int, int], tuple[float, float]] = {}

    for row in range(5):
        for col in range(5):
            latitude = lat_min + (lat_span * row / 4)
            longitude = lon_min + (lon_span * col / 4)
            points[(row, col)] = (latitude, longitude)
            graph.add_node((row, col), latitude=latitude, longitude=longitude)

    for row, col in points:
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            neighbor = (row + dr, col + dc)
            if neighbor not in points:
                continue
            lat1, lon1 = points[(row, col)]
            lat2, lon2 = points[neighbor]
            weight = haversine_km(lat1, lon1, lat2, lon2)
            graph.add_edge((row, col), neighbor, weight=weight)

    graph.graph["origin"] = origin
    graph.graph["destination"] = destination
    return graph


def try_osmnx_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    blocked: list[tuple[float, float]] | None = None,
) -> dict | None:
    """Use OSMnx when available, while retaining NetworkX fallback routing."""
    try:
        import osmnx as ox

        midpoint = (
            (origin[0] + destination[0]) / 2,
            (origin[1] + destination[1]) / 2,
        )
        distance = max(3000.0, haversine_km(*origin, *destination) * 1000 * 1.5)
        distance = min(distance, 50000.0)
        GRAPH_CACHE.mkdir(parents=True, exist_ok=True)
        cache_path = GRAPH_CACHE / (
            f"osm_{midpoint[0]:.3f}_{midpoint[1]:.3f}_{distance:.0f}.graphml"
        )
        if cache_path.exists():
            graph = ox.load_graphml(cache_path)
        else:
            graph = ox.graph_from_point(midpoint, dist=distance, network_type="drive")
            ox.save_graphml(graph, filepath=cache_path)

        origin_node = ox.distance.nearest_nodes(graph, origin[1], origin[0])
        destination_node = ox.distance.nearest_nodes(graph, destination[1], destination[0])
        for u, v, key, data in graph.edges(keys=True, data=True):
            multiplier = 1.0
            lat_u = graph.nodes[u].get("y", 0.0)
            lon_u = graph.nodes[u].get("x", 0.0)
            lat_v = graph.nodes[v].get("y", 0.0)
            lon_v = graph.nodes[v].get("x", 0.0)
            for blocked_lat, blocked_lon in blocked or []:
                if (
                    min(
                        haversine_km(lat_u, lon_u, blocked_lat, blocked_lon),
                        haversine_km(lat_v, lon_v, blocked_lat, blocked_lon),
                    )
                    <= 2.0
                ):
                    multiplier = 10.0
            data["weight"] = float(data.get("length", 1.0)) * multiplier

        route_nodes = nx.shortest_path(graph, origin_node, destination_node, weight="weight")
        route_coordinates = [
            {"latitude": graph.nodes[node]["y"], "longitude": graph.nodes[node]["x"]}
            for node in route_nodes
        ]
        if len(route_coordinates) < 2:
            return None
        distance_m = nx.path_weight(graph, route_nodes, weight="weight")
        return {
            "route": route_coordinates,
            "distance_km": round(distance_m / 1000, 2),
            "routing_mode": "OSMnx + NetworkX cached graph",
            "graph_cache_path": str(cache_path),
        }
    except Exception:
        return None


def evacuate_route(
    latitude: float,
    longitude: float,
    hazard: str | None = None,
    blocked: list[tuple[float, float]] | None = None,
) -> dict:
    shelter = nearest_shelters(latitude, longitude, limit=1)[0]
    origin = (latitude, longitude)
    destination = (float(shelter["latitude"]), float(shelter["longitude"]))

    osmnx_result = try_osmnx_route(origin, destination, blocked)
    if osmnx_result is not None:
        return {
            "origin": {"latitude": latitude, "longitude": longitude},
            "destination": shelter,
            "route": osmnx_result["route"],
            "distance_km": osmnx_result["distance_km"],
            "hazard": hazard,
            "blocked_coordinates": blocked or [],
            "routing_mode": osmnx_result["routing_mode"],
            "graph_cache_path": osmnx_result["graph_cache_path"],
        }

    graph = build_fallback_graph(origin, destination)
    origin_node = (0, 0)
    destination_node = (4, 4)
    graph.nodes[origin_node]["latitude"] = latitude
    graph.nodes[origin_node]["longitude"] = longitude
    graph.nodes[destination_node]["latitude"] = destination[0]
    graph.nodes[destination_node]["longitude"] = destination[1]

    # Road-blockage reports dynamically increase or block nearby edge weights.
    for u, v, data in graph.edges(data=True):
        lat_u, lon_u = graph.nodes[u]["latitude"], graph.nodes[u]["longitude"]
        lat_v, lon_v = graph.nodes[v]["latitude"], graph.nodes[v]["longitude"]
        edge_weight = float(data["weight"])
        for blocked_lat, blocked_lon in blocked or []:
            distance = min(
                haversine_km(lat_u, lon_u, blocked_lat, blocked_lon),
                haversine_km(lat_v, lon_v, blocked_lat, blocked_lon),
            )
            if distance <= 2.0:
                edge_weight *= 10.0
        data["weight"] = edge_weight

    route_nodes = nx.shortest_path(graph, origin_node, destination_node, weight="weight")
    route_coordinates = [
        {
            "latitude": graph.nodes[node]["latitude"],
            "longitude": graph.nodes[node]["longitude"],
        }
        for node in route_nodes
    ]
    distance = nx.path_weight(graph, route_nodes, weight="weight")

    GRAPH_CACHE.mkdir(parents=True, exist_ok=True)
    cache_key = (
        f"route_{latitude:.3f}_{longitude:.3f}_{destination[0]:.3f}_{destination[1]:.3f}.json"
    )
    cache_path = GRAPH_CACHE / cache_key
    cache_path.write_text(json.dumps(route_coordinates), encoding="utf-8")

    return {
        "origin": {"latitude": latitude, "longitude": longitude},
        "destination": shelter,
        "route": route_coordinates,
        "distance_km": round(distance, 2),
        "hazard": hazard,
        "blocked_coordinates": blocked or [],
        "routing_mode": "NetworkX local fallback grid",
        "graph_cache_path": str(cache_path),
    }
