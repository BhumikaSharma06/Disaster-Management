"""Read-only endpoints for open telemetry ingestion."""

from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services.telemetry import (
    GDACSProvider,
    OpenMeteoElevationProvider,
    OpenMeteoFloodProvider,
    OpenMeteoWeatherProvider,
    TelemetryIngestion,
    load_sentinel_coordinates,
)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/sentinels")
async def fetch_sentinel_telemetry(
    west: float | None = None,
    south: float | None = None,
    east: float | None = None,
    north: float | None = None,
) -> dict:
    """Fetch the configured sentinel grid from open weather, flood, and alert providers."""
    try:
        async with httpx.AsyncClient() as client:
            ingestion = TelemetryIngestion(
                flood=OpenMeteoFloodProvider(client),
                weather=OpenMeteoWeatherProvider(client),
                elevation=OpenMeteoElevationProvider(client),
                gdacs=GDACSProvider(client),
            )
            sentinel_path = (
                Path(settings.telemetry_sentinels_path)
                if settings.telemetry_sentinels_path
                else None
            )
            bbox = None
            if all(value is not None for value in (west, south, east, north)):
                bbox = (west, south, east, north)
            return await ingestion.fetch_sentinel_grid(
                load_sentinel_coordinates(sentinel_path), bbox=bbox
            )
    except (httpx.HTTPError, ValueError, KeyError) as error:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve open telemetry from one or more providers",
        ) from error
