"""Tests for V1 shelters, routing, translation, and status services."""

import asyncio
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.services.geocoding import _administrative_address, _similar_places
from app.services.routing import evacuate_route, nearest_shelters
from app.services.translation import TranslationService

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_database():
    """Keep these endpoint checks independent of a running PostgreSQL service."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_geocode_endpoint_accepts_place_query(monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_search_places(query: str, limit: int = 5) -> dict:
        del query, limit
        return {
            "provider": "google-maps-geocoding",
            "available": True,
            "results": [
                {
                    "name": "Supaul, Bihar",
                    "display_name": "Supaul, Bihar, India",
                    "latitude": 26.126,
                    "longitude": 86.605,
                    "place_id": "test-place",
                    "types": ["administrative_area_level_2"],
                }
            ],
        }

    monkeypatch.setattr("app.api.core_v1.search_places", mock_search_places)
    response = client.get("/api/v1/geocode", params={"q": "Supaul, Bihar", "limit": 3})

    assert response.status_code == 200
    payload = response.json()
    assert "provider" in payload
    assert "available" in payload
    assert "results" in payload


def test_reverse_geocode_endpoint_returns_administrative_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_reverse_geocode(latitude: float, longitude: float) -> dict:
        assert latitude == 26.1
        assert longitude == 86.4
        return {
            "provider": "test-provider",
            "available": True,
            "state": "Example State",
            "district": "Example District",
            "locality": "Example Ward",
            "display_name": "Example Ward, Example District, Example State",
        }

    monkeypatch.setattr("app.api.core_v1.reverse_geocode", mock_reverse_geocode)
    response = client.get(
        "/api/v1/geocode/reverse",
        params={"lat": 26.1, "lon": 86.4},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "Example State"
    assert response.json()["district"] == "Example District"
    assert response.json()["locality"] == "Example Ward"


def test_reverse_geocode_maps_nominatim_address_to_request_fields() -> None:
    address = _administrative_address(
        [
            {"types": ["state"], "long_name": "Example State"},
            {"types": ["state_district"], "long_name": "Example District"},
            {"types": ["hamlet"], "long_name": "Example Ward"},
        ],
        "Example Ward, Example District, Example State",
        google=False,
    )

    assert address == {
        "state": "Example State",
        "district": "Example District",
        "locality": "Example Ward",
        "display_name": "Example Ward, Example District, Example State",
    }


def test_reverse_geocode_requires_all_administrative_fields() -> None:
    address = _administrative_address(
        [{"types": ["state"], "long_name": "Example State"}],
        "Example State",
        google=False,
    )

    assert address is None


def test_similar_place_fallback_suggests_misspelled_location() -> None:
    results = _similar_places("Jipur", 5)

    assert results
    assert any("Jaipur" in result["name"] for result in results)
    assert all(result["provider"] == "aapdasetu-sentinel-fallback" for result in results)


def test_status_endpoint_is_available() -> None:
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["shelters"]["available"] is False
    assert payload["routing"]["available"] is True
    assert payload["translation"]["available"] is True


def test_sos_endpoint_surfaces_database_unavailability() -> None:
    response = client.get("/api/v1/sos")

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to retrieve SOS records from the database."


def test_nearest_shelter_lookup_is_pan_india() -> None:
    shelters = nearest_shelters(28.6139, 77.2090, 3)

    assert len(shelters) == 3
    assert shelters[0]["distance_km"] >= 0
    assert all(item["verification_status"] == "unverified" for item in shelters)


def test_fallback_evacuation_route() -> None:
    result = evacuate_route(28.6139, 77.2090, hazard="heatwave", blocked=[(28.6200, 77.2100)])

    assert result["origin"]["latitude"] == 28.6139
    assert result["destination"]
    assert len(result["route"]) >= 2
    assert result["distance_km"] >= 0


def test_local_translation_and_mock_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class OfflineTranslator:
        def __init__(self, source: str, target: str) -> None:
            del source, target

        def translate(self, text: str) -> str:
            return text

    monkeypatch.setitem(
        sys.modules,
        "deep_translator",
        SimpleNamespace(GoogleTranslator=OfflineTranslator),
    )

    async def exercise() -> None:
        service = TranslationService()
        result = await service.translate(
            "Follow instructions from authorized local emergency services.", "hi"
        )
        dispatch = await service.dispatch(
            {
                "message": "Follow instructions from authorized local emergency services.",
                "checklist": ["Follow instructions from authorized local emergency services."],
            },
            "hi",
        )

        assert result["provider"] in {
            "local-cache",
            "english-fallback",
            "google-translator",
            "bhashini",
        }
        assert dispatch["channel"] == "mock-sms-push"
        assert dispatch["delivery_status"] == "dispatched"

    asyncio.run(exercise())


def test_local_readiness_coordinate_check() -> None:
    response = client.get(
        "/api/v1/local-readiness",
        params={"lat": 28.6139, "lon": 77.2090},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["coordinates"] == {"latitude": 28.6139, "longitude": 77.2090}
    assert "live_hazard_feed" in payload
    assert "verified_shelters" in payload
    assert payload["route_available"] is True


def test_v1_shelter_endpoint_validation() -> None:
    response = client.get("/api/v1/shelters/nearest", params={"lat": 28.6139, "lon": 77.2090})

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["verified"] is False
    assert payload["shelters"]
