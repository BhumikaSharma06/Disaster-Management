"""Tests for environment-based application configuration."""

from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_default_database_url_uses_compose_host_port(monkeypatch) -> None:
    """Local backend defaults to the host port published by Docker Compose."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5433")
    monkeypatch.setenv("POSTGRES_USER", "aapdasetu")
    monkeypatch.setenv("POSTGRES_PASSWORD", "change-me-for-local-development")
    monkeypatch.setenv("POSTGRES_DB", "aapdasetu")

    database_url = make_url(Settings.from_env().database_url)

    assert database_url.host == "localhost"
    assert database_url.port == 5433
    assert database_url.database == "aapdasetu"


def test_database_credentials_with_url_reserved_characters_are_encoded(
    monkeypatch,
) -> None:
    """URL components safely encode reserved characters in credentials."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_HOST", "db")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "test-user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:word/path%")
    monkeypatch.setenv("POSTGRES_DB", "test-db")

    database_url = make_url(Settings.from_env().database_url)

    assert database_url.username == "test-user"
    assert database_url.password == "p@ss:word/path%"
    assert database_url.host == "db"
    assert database_url.port == 5432
    assert database_url.database == "test-db"
