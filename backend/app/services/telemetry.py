"""Async, unauthenticated telemetry provider adapters for Open-Meteo and GDACS."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

USER_AGENT = "AapdaSetu-Prototype/1.0 (disaster-management research; +https://localhost)"


class TelemetryProvider(Protocol):
    """Contract for real-time and replay-compatible telemetry adapters."""

    async def fetch(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        """Fetch telemetry and return a provider-native JSON response."""


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any],
    timeout: float = 20,
    attempts: int = 3,
) -> httpx.Response:
    """Retry transient provider failures with a polite user agent."""
    last_error: Exception | None = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for attempt in range(attempts):
        try:
            response = await client.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code in (429, 502, 503, 504):
                last_error = httpx.HTTPStatusError(
                    f"provider returned {response.status_code}",
                    request=response.request,
                    response=response,
                )
            else:
                return response
        except httpx.HTTPError as error:
            last_error = error
        if attempt + 1 < attempts:
            await asyncio.sleep(0.5 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise httpx.HTTPError("telemetry request failed")


@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float
    basin: str
    region: str


def load_sentinel_coordinates(path: Path | None = None) -> list[Coordinate]:
    """Load the configurable basin/coastal sentinel grid from JSON."""
    sentinel_path = path or Path(__file__).resolve().parents[1] / "config" / "pan_india_nodes.json"
    with sentinel_path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)

    sentinels = payload.get("sentinels")
    if not isinstance(sentinels, list) or not sentinels:
        raise ValueError("sentinel configuration must contain a non-empty sentinels list")

    return [
        Coordinate(
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            basin=str(item["basin"]),
            region=str(item["region"]),
        )
        for item in sentinels
    ]


class OpenMeteoFloodProvider:
    """Open-Meteo Global Flood API adapter."""

    endpoint = "https://flood-api.open-meteo.com/v1/flood"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        lat_values, lon_values = _coordinate_arrays(latitude, longitude, latitudes, longitudes)
        response = await _get_with_retry(
            self._client,
            self.endpoint,
            params={
                "latitude": lat_values,
                "longitude": lon_values,
                "daily": "river_discharge,river_discharge_mean,river_discharge_max",
                "forecast_days": 7,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


class OpenMeteoWeatherProvider:
    """Open-Meteo Weather API adapter for forecast weather and soil variables."""

    endpoint = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        lat_values, lon_values = _coordinate_arrays(latitude, longitude, latitudes, longitudes)
        response = await _get_with_retry(
            self._client,
            self.endpoint,
            params={
                "latitude": lat_values,
                "longitude": lon_values,
                "hourly": "precipitation,rain,soil_moisture_0_to_7cm,"
                "soil_moisture_7_to_28cm,soil_moisture_28_to_100cm,"
                "soil_moisture_100_to_255cm,wind_speed_10m,wind_gusts_10m,"
                "surface_pressure,temperature_2m,apparent_temperature,"
                "relative_humidity_2m",
                "forecast_days": 7,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


class OpenMeteoElevationProvider:
    """Open-Meteo Elevation API adapter."""

    endpoint = "https://api.open-meteo.com/v1/elevation"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        lat_values, lon_values = _coordinate_arrays(latitude, longitude, latitudes, longitudes)
        response = await _get_with_retry(
            self._client,
            self.endpoint,
            params={"latitude": lat_values, "longitude": lon_values},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


class GDACSProvider:
    """GDACS event and GeoJSON polygon adapter for selected event types."""

    endpoint = (
        "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
        "?eventlist=FL;TC;DR&country=India"
    )

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {"eventlist": "FL;TC;DR", "country": "India"}
        if bbox is not None:
            west, south, east, north = bbox
            params.update({"bbox": f"{west},{south},{east},{north}"})
        response = await _get_with_retry(self._client, self.endpoint, params=params, timeout=20)
        response.raise_for_status()
        return response.json()


class TelemetryIngestion:
    """Coordinates batched Open-Meteo and GDACS fetches across a sentinel grid."""

    def __init__(
        self,
        flood: TelemetryProvider,
        weather: TelemetryProvider,
        elevation: TelemetryProvider,
        gdacs: TelemetryProvider,
    ) -> None:
        self.flood = flood
        self.weather = weather
        self.elevation = elevation
        self.gdacs = gdacs

    async def fetch_sentinel_grid(
        self,
        coordinates: list[Coordinate],
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        """Fetch all provider families in one batched call per provider family."""
        latitudes = [coordinate.latitude for coordinate in coordinates]
        longitudes = [coordinate.longitude for coordinate in coordinates]

        flood = await self.flood.fetch(latitudes=latitudes, longitudes=longitudes)
        weather = await self.weather.fetch(latitudes=latitudes, longitudes=longitudes)
        elevation = await self.elevation.fetch(latitudes=latitudes, longitudes=longitudes)
        alerts = await self.gdacs.fetch(bbox=bbox)

        return {
            "coordinates": [
                {
                    "basin": coordinate.basin,
                    "region": coordinate.region,
                    "latitude": coordinate.latitude,
                    "longitude": coordinate.longitude,
                }
                for coordinate in coordinates
            ],
            "flood": flood,
            "weather": weather,
            "elevation": elevation,
            "gdacs": alerts,
        }


def _coordinate_arrays(
    latitude: float | None,
    longitude: float | None,
    latitudes: list[float] | None,
    longitudes: list[float] | None,
) -> tuple[list[float], list[float]]:
    if latitudes is not None or longitudes is not None:
        if latitudes is None or longitudes is None:
            raise ValueError("latitudes and longitudes must be provided together")
        if len(latitudes) != len(longitudes):
            raise ValueError("latitudes and longitudes must have the same length")
        if not latitudes:
            raise ValueError("at least one coordinate pair is required")
        return latitudes, longitudes
    if latitude is None or longitude is None:
        raise ValueError("provide latitude/longitude or coordinate arrays")
    return [latitude], [longitude]
