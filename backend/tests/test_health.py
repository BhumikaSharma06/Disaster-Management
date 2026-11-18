"""Tests for the API liveness route."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    """The health route responds without requiring a database connection."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
