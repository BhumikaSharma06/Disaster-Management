"""Tests for open telemetry provider adapters and sentinel batching."""

from __future__ import annotations

import asyncio

import httpx

from app.services.telemetry import (
    Coordinate,
    GDACSProvider,
    OpenMeteoElevationProvider,
    OpenMeteoFloodProvider,
    OpenMeteoWeatherProvider,
    TelemetryIngestion,
    load_sentinel_coordinates,
)


def test_load_sentinel_coordinates() -> None:
    coordinates = load_sentinel_coordinates()

    assert coordinates
    assert all(item.latitude and item.longitude for item in coordinates)
    assert all(item.basin and item.region for item in coordinates)


def test_open_meteo_providers_batch_coordinates() -> None:
    async def exercise() -> None:
        seen: list[tuple[str, dict[str, object]]] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            params = {key: request.url.params.get_list(key) for key in request.url.params.keys()}
            seen.append((request.url.host, params))
            if "gdacsapi" in request.url.host:
                return httpx.Response(200, json={"features": []})
            return httpx.Response(200, json={"ok": True})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            latitudes = [25.4358, 26.1445]
            longitudes = [81.8463, 91.7362]

            await OpenMeteoFloodProvider(client).fetch(latitudes=latitudes, longitudes=longitudes)
            await OpenMeteoWeatherProvider(client).fetch(latitudes=latitudes, longitudes=longitudes)
            await OpenMeteoElevationProvider(client).fetch(
                latitudes=latitudes, longitudes=longitudes
            )
            await GDACSProvider(client).fetch()

        flood_params = seen[0][1]
        assert flood_params["latitude"] == ["25.4358", "26.1445"]
        assert flood_params["longitude"] == ["81.8463", "91.7362"]
        assert "river_discharge" in str(flood_params["daily"])

        weather_params = seen[1][1]
        assert "soil_moisture_0_to_7cm" in str(weather_params["hourly"])
        assert "wind_gusts_10m" in str(weather_params["hourly"])

    asyncio.run(exercise())


class StubProvider:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    async def fetch(self, **kwargs: object) -> dict[str, object]:
        return self.payload


def test_telemetry_ingestion_uses_one_array_request_per_family() -> None:
    async def exercise() -> None:
        ingestion = TelemetryIngestion(
            flood=StubProvider({"river_discharge": [1]}),
            weather=StubProvider({"temperature_2m": [25]}),
            elevation=StubProvider({"elevation": [100]}),
            gdacs=StubProvider({"features": []}),
        )
        result = await ingestion.fetch_sentinel_grid(
            [
                Coordinate(25.4, 81.8, "Ganga", "Middle Ganga"),
                Coordinate(26.1, 91.7, "Brahmaputra", "Assam Valley"),
            ]
        )

        assert result["flood"] == {"river_discharge": [1]}
        assert result["weather"] == {"temperature_2m": [25]}
        assert len(result["coordinates"]) == 2

    asyncio.run(exercise())
