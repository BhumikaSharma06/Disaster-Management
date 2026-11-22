"""Periodic open-provider ingestion and in-memory live forecast/alert state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.hazards.registry import registry
from app.services.telemetry import (
    GDACSProvider,
    OpenMeteoElevationProvider,
    OpenMeteoFloodProvider,
    OpenMeteoWeatherProvider,
    TelemetryIngestion,
    load_sentinel_coordinates,
)


class LiveDataState:
    """Bounded in-process latest snapshot for prototype live endpoints."""

    def __init__(self) -> None:
        self.last_update: datetime | None = None
        self.last_error: str | None = None
        self.telemetry: dict[str, Any] = {}
        self.risk_scores: list[dict[str, Any]] = []

    async def poll(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                ingestion = TelemetryIngestion(
                    flood=OpenMeteoFloodProvider(client),
                    weather=OpenMeteoWeatherProvider(client),
                    elevation=OpenMeteoElevationProvider(client),
                    gdacs=GDACSProvider(client),
                )
                snapshot = await ingestion.fetch_sentinel_grid(load_sentinel_coordinates())
            self.telemetry = snapshot
            self.risk_scores = self._compute_risk_scores(snapshot)
            self.last_update = datetime.now(timezone.utc)
            self.last_error = None
        except Exception as error:
            self.last_error = f"{type(error).__name__}: {error}"
        return self.status()

    def _compute_risk_scores(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        flood = registry.get("flood")
        if flood is None:
            return []

        scores: list[dict[str, Any]] = []
        weather = snapshot.get("weather")
        elevation = snapshot.get("elevation")
        discharge = snapshot.get("flood")
        gdacs = snapshot.get("gdacs")

        weather_values = weather if isinstance(weather, list) else [weather]
        elevation_values = elevation if isinstance(elevation, list) else [elevation]
        flood_values = discharge if isinstance(discharge, list) else [discharge]
        gdacs_features = gdacs.get("features", []) if isinstance(gdacs, dict) else []

        for index, coordinate in enumerate(snapshot.get("coordinates", [])):
            weather_item = (
                weather_values[index]
                if index < len(weather_values)
                else weather_values[0]
                if weather_values
                else {}
            )
            elevation_item = (
                elevation_values[index]
                if index < len(elevation_values)
                else elevation_values[0]
                if elevation_values
                else {}
            )
            flood_item = (
                flood_values[index]
                if index < len(flood_values)
                else flood_values[0]
                if flood_values
                else {}
            )

            precipitation = _extract_number(weather_item, "precipitation")
            soil = _extract_number(weather_item, "soil_moisture_0_to_7cm")
            elevation_m = _extract_number(elevation_item, "elevation", 100.0)
            river_discharge = _extract_number(flood_item, "river_discharge")
            observations = {
                "precipitation": precipitation,
                "soil_moisture": soil,
                "elevation": elevation_m,
                "river_discharge": river_discharge,
                "gdacs_features": len(gdacs_features),
            }
            payload = flood.generate_alert_payload(observations)
            scores.append(
                {
                    "basin": coordinate["basin"],
                    "region": coordinate["region"],
                    "latitude": coordinate["latitude"],
                    "longitude": coordinate["longitude"],
                    "score": payload["score"],
                    "level": payload["level"],
                    "hazard_type": "flood",
                    "message": payload["message"],
                    "source": "Open-Meteo and GDACS prototype indicators",
                }
            )
        return scores

    def status(self) -> dict[str, Any]:
        return {
            "initialized": self.last_update is not None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_error": self.last_error,
            "sentinel_count": len(self.telemetry.get("coordinates", [])),
            "risk_score_count": len(self.risk_scores),
            "gdacs_reachable": self.last_error is None and bool(self.telemetry),
        }


live_data = LiveDataState()


def _extract_number(payload: Any, key: str, default: float = 0.0) -> float:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key, default)
    if isinstance(value, dict):
        values = [item for item in value.values() if isinstance(item, (int, float))]
        return float(sum(values) / len(values)) if values else default
    if isinstance(value, list):
        numeric = [float(item) for item in value if isinstance(item, (int, float))]
        return float(max(numeric)) if numeric else default
    if isinstance(value, (int, float)):
        return float(value)
    return default
