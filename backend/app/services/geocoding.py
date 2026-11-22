"""District/place geocoding provider with Google Maps and open fallback support."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path

import httpx

from app.core.config import settings

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "AapdaSetu-Prototype/1.0 (disaster-management research)"
GEOCODE_CACHE_TTL_SECONDS = 600
GEOCODE_CACHE_MAX_ENTRIES = 256
_geocode_cache: dict[tuple[str, int], tuple[float, dict]] = {}


def _similar_places(query: str, limit: int) -> list[dict]:
    """Rank configured regional sentinels as safe fallback suggestions."""
    config_path = Path(__file__).resolve().parents[1] / "config" / "pan_india_nodes.json"
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            sentinels = json.load(stream).get("sentinels", [])
    except (OSError, json.JSONDecodeError):
        sentinels = []

    normalized = query.lower().strip()
    ranked: list[tuple[float, dict]] = []
    seen: set[tuple[float, float]] = set()

    for sentinel in sentinels:
        region = str(sentinel.get("region", "")).strip()
        basin = str(sentinel.get("basin", "")).strip()
        if not region:
            continue

        latitude = float(sentinel["latitude"])
        longitude = float(sentinel["longitude"])
        key = (round(latitude, 4), round(longitude, 4))
        if key in seen:
            continue
        seen.add(key)

        region_score = SequenceMatcher(None, normalized, region.lower()).ratio()
        basin_score = SequenceMatcher(None, normalized, basin.lower()).ratio()
        score = max(region_score, basin_score)
        if score < 0.28:
            continue

        ranked.append(
            (
                score,
                {
                    "name": region,
                    "display_name": f"{region}, {basin}, India",
                    "latitude": latitude,
                    "longitude": longitude,
                    "place_id": (
                        f"sentinel-{basin.lower().replace(' ', '-')}-"
                        f"{region.lower().replace(' ', '-')}"
                    ),
                    "types": ["aapdasetu_sentinel", "similar_place"],
                    "similarity": round(score, 2),
                    "provider": "aapdasetu-sentinel-fallback",
                },
            )
        )

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in ranked[:limit]]


async def search_places(query: str, limit: int = 5) -> dict:
    """Search India place names using configured Google Maps, then open fallback."""
    query = query.strip()
    if not query:
        return {"provider": "none", "available": False, "results": []}

    cache_key = (query.casefold(), limit)
    cached = _geocode_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return deepcopy(cached[1])
    _geocode_cache.pop(cache_key, None)

    async with httpx.AsyncClient() as client:
        provider_results: list[dict] = []
        provider_name = "none"

        if settings.google_maps_api_key:
            try:
                google_results = await _search_google(client, query, limit)
                if google_results:
                    provider_results = google_results
                    provider_name = "google-maps-geocoding"
            except httpx.HTTPError:
                pass

        if not provider_results:
            try:
                fallback_results = await _search_nominatim(client, query, limit)
                if fallback_results:
                    provider_results = fallback_results
                    provider_name = "openstreetmap-nominatim"
            except httpx.HTTPError:
                pass

        local_results = _similar_places(query, limit)
        if provider_results:
            provider_results.sort(
                key=lambda result: max(
                    SequenceMatcher(
                        None,
                        query.lower(),
                        str(result.get("name", "")).lower(),
                    ).ratio(),
                    SequenceMatcher(
                        None,
                        query.lower(),
                        str(result.get("display_name", "")).lower(),
                    ).ratio(),
                ),
                reverse=True,
            )
            seen = {
                (round(float(result["latitude"]), 4), round(float(result["longitude"]), 4))
                for result in provider_results
            }
            for local in local_results:
                key = (round(local["latitude"], 4), round(local["longitude"], 4))
                if key not in seen:
                    provider_results.append(local)
                    seen.add(key)

        if provider_results:
            result = {
                "provider": provider_name,
                "available": True,
                "results": provider_results[:limit],
                "has_local_suggestions": any(
                    result.get("provider") == "aapdasetu-sentinel-fallback"
                    for result in provider_results
                ),
            }
            if len(_geocode_cache) >= GEOCODE_CACHE_MAX_ENTRIES:
                oldest_key = min(_geocode_cache, key=lambda key: _geocode_cache[key][0])
                _geocode_cache.pop(oldest_key)
            _geocode_cache[cache_key] = (
                time.monotonic() + GEOCODE_CACHE_TTL_SECONDS,
                deepcopy(result),
            )
            return result

        if local_results:
            result = {
                "provider": "aapdasetu-sentinel-fallback",
                "available": True,
                "results": local_results,
                "has_local_suggestions": True,
                "message": "No exact location match was found. Showing similar configured areas.",
            }
            if len(_geocode_cache) >= GEOCODE_CACHE_MAX_ENTRIES:
                oldest_key = min(_geocode_cache, key=lambda key: _geocode_cache[key][0])
                _geocode_cache.pop(oldest_key)
            _geocode_cache[cache_key] = (
                time.monotonic() + GEOCODE_CACHE_TTL_SECONDS,
                deepcopy(result),
            )
            return result

        return {
            "provider": "none",
            "available": False,
            "results": [],
            "message": "No matching or similar place was found. Try a district or state name.",
        }


async def reverse_geocode(latitude: float, longitude: float) -> dict:
    """Resolve coordinates to administrative address fields using configured providers."""
    async with httpx.AsyncClient() as client:
        if settings.google_maps_api_key:
            try:
                address = await _reverse_google(client, latitude, longitude)
                if address:
                    return {"provider": "google-maps-geocoding", "available": True, **address}
            except httpx.HTTPError:
                pass

        try:
            address = await _reverse_nominatim(client, latitude, longitude)
        except httpx.HTTPError:
            address = None
        if address:
            return {"provider": "openstreetmap-nominatim", "available": True, **address}

    return {
        "provider": "none",
        "available": False,
        "message": "Could not resolve this location to state, district, and locality.",
    }


async def _reverse_google(
    client: httpx.AsyncClient,
    latitude: float,
    longitude: float,
) -> dict | None:
    response = await client.get(
        GOOGLE_GEOCODE_URL,
        params={
            "latlng": f"{latitude},{longitude}",
            "key": settings.google_maps_api_key,
        },
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK":
        return None

    results = payload.get("results", [])
    for result in results:
        address = _administrative_address(
            result.get("address_components", []),
            result.get("formatted_address", ""),
            google=True,
        )
        if address:
            return address
    return None


async def _reverse_nominatim(
    client: httpx.AsyncClient,
    latitude: float,
    longitude: float,
) -> dict | None:
    response = await client.get(
        NOMINATIM_REVERSE_URL,
        params={
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
        },
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    address = payload.get("address", {})
    locality = next(
        (
            address.get(key)
            for key in (
                "village",
                "town",
                "city",
                "municipality",
                "hamlet",
                "suburb",
                "neighbourhood",
                "city_district",
                "quarter",
            )
            if address.get(key)
        ),
        None,
    )
    district = address.get("state_district") or address.get("district") or address.get("county")
    if not address.get("state") or not district or not locality:
        return None
    return {
        "state": address["state"],
        "district": district,
        "locality": locality,
        "display_name": payload.get("display_name", ""),
    }


def _administrative_address(
    components: list[dict], display_name: str, *, google: bool
) -> dict | None:
    by_type = {
        component_type: component.get("long_name")
        for component in components
        for component_type in component.get("types", [])
    }
    if google:
        state = by_type.get("administrative_area_level_1")
        district = by_type.get("administrative_area_level_2")
        locality = next(
            (
                by_type.get(component_type)
                for component_type in (
                    "sublocality_level_1",
                    "locality",
                    "administrative_area_level_3",
                    "neighborhood",
                )
                if by_type.get(component_type)
            ),
            None,
        )
    else:
        state = by_type.get("state")
        district = by_type.get("state_district") or by_type.get("district") or by_type.get("county")
        locality = next(
            (
                by_type.get(component_type)
                for component_type in (
                    "village",
                    "town",
                    "city",
                    "municipality",
                    "hamlet",
                    "suburb",
                    "neighbourhood",
                    "city_district",
                    "quarter",
                )
                if by_type.get(component_type)
            ),
            None,
        )
    if not state or not district or not locality:
        return None
    return {
        "state": state,
        "district": district,
        "locality": locality,
        "display_name": display_name,
    }


async def _search_google(
    client: httpx.AsyncClient,
    query: str,
    limit: int,
) -> list[dict]:
    response = await client.get(
        GOOGLE_GEOCODE_URL,
        params={
            "address": f"{query}, India",
            "components": "country:IN",
            "key": settings.google_maps_api_key,
        },
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
        return []

    results = []
    for item in payload.get("results", [])[:limit]:
        location = item.get("geometry", {}).get("location", {})
        latitude = location.get("lat")
        longitude = location.get("lng")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            continue
        results.append(
            {
                "name": item.get("formatted_address", query),
                "display_name": item.get("formatted_address", query),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "place_id": item.get("place_id"),
                "types": item.get("types", []),
            }
        )
    return results


async def _search_nominatim(
    client: httpx.AsyncClient,
    query: str,
    limit: int,
) -> list[dict]:
    response = await client.get(
        NOMINATIM_URL,
        params={"q": f"{query}, India", "format": "jsonv2", "limit": limit, "countrycodes": "in"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()

    results = []
    for item in payload[:limit]:
        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        results.append(
            {
                "name": item.get("name") or item.get("display_name", query),
                "display_name": item.get("display_name", query),
                "latitude": latitude,
                "longitude": longitude,
                "place_id": item.get("place_id"),
                "types": [item.get("type")] if item.get("type") else [],
            }
        )
    return results
