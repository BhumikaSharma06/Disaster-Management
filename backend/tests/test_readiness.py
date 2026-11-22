"""Tests for the database readiness endpoint."""

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api import health
from app.main import app

client = TestClient(app)


def test_readiness_reports_database_connection(monkeypatch) -> None:
    """The readiness endpoint reports a successful database probe."""
    monkeypatch.setattr(health.engine, "connect", lambda: _ConnectionContext())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_reports_database_unavailable(monkeypatch) -> None:
    """Database connection failures make readiness fail without affecting liveness."""
    monkeypatch.setattr(
        health.engine,
        "connect",
        lambda: _raise_database_error(),
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}
    assert client.get("/health").status_code == 200


class _ConnectionContext:
    """Minimal connection context manager for the readiness unit test."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        return None


def _raise_database_error():
    """Raise the same exception class used for SQLAlchemy connection failures."""
    raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))
