"""Pytest configuration and global fixtures for backend tests."""

import pytest

from app.services.live_data import live_data


@pytest.fixture(autouse=True)
def disable_live_telemetry_polling(monkeypatch: pytest.MonkeyPatch):
    """Prevent unmocked external network requests to telemetry providers during tests."""

    async def mock_poll():
        return live_data.status()

    monkeypatch.setattr(live_data, "poll", mock_poll)
