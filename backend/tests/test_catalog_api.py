"""Tests for the read-only region and shelter APIs."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app

client = TestClient(app)

REGION = {
    "id": 7,
    "name": "Example area",
    "region_type": "district",
    "district_name": "Example district",
    "parent_id": None,
    "source_name": "Example municipal dataset",
    "source_reference": "record 17",
    "source_license": None,
    "verification_status": "unverified",
    "verified_at": None,
    "verified_by": None,
    "boundary": (
        '{"type":"MultiPolygon","coordinates":[[[[86.0,25.0],[87.0,25.0],'
        "[87.0,26.0],[86.0,26.0],[86.0,25.0]]]]}"
    ),
}

SHELTERS = [
    {
        "id": 11,
        "name": "Example shelter",
        "region_id": 7,
        "capacity": 120,
        "current_occupancy": 18,
        "source_name": "Example municipal dataset",
        "source_reference": "shelter 11",
        "source_license": None,
        "verification_status": "unverified",
        "verified_at": None,
        "verified_by": None,
        "location": '{"type":"Point","coordinates":[86.5,25.5]}',
    },
    {
        "id": 12,
        "name": "Another shelter",
        "region_id": 8,
        "capacity": None,
        "current_occupancy": 0,
        "source_name": "Unspecified (legacy record)",
        "source_reference": None,
        "source_license": None,
        "verification_status": "unverified",
        "verified_at": None,
        "verified_by": None,
        "location": '{"type":"Point","coordinates":[87.5,26.5]}',
    },
]


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeSession:
    def __init__(self) -> None:
        self.fail = False
        self.empty = False
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> _FakeResult:
        self.statements.append(statement)
        if self.fail:
            raise OperationalError("SELECT", {}, RuntimeError("database unavailable"))

        table_name = statement.get_final_froms()[0].name
        rows = [REGION] if table_name == "regions" else SHELTERS
        if self.empty:
            rows = []
        params = statement.compile().params
        requested_region_id = next(
            (value for key, value in params.items() if key.startswith("region_id")),
            None,
        )
        if requested_region_id is not None:
            rows = [row for row in rows if row["region_id"] == requested_region_id]
        return _FakeResult(rows)


@pytest.fixture
def db_session() -> Iterator[_FakeSession]:
    session = _FakeSession()

    def override_get_db() -> Iterator[_FakeSession]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)


def test_list_regions_returns_geojson_boundaries(db_session: _FakeSession) -> None:
    response = client.get("/api/regions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 7,
            "name": "Example area",
            "region_type": "district",
            "district_name": "Example district",
            "parent_id": None,
            "source_name": "Example municipal dataset",
            "source_reference": "record 17",
            "source_license": None,
            "verification_status": "unverified",
            "verified_at": None,
            "verified_by": None,
            "boundary": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[86.0, 25.0], [87.0, 25.0], [87.0, 26.0], [86.0, 26.0], [86.0, 25.0]]]
                ],
            },
        }
    ]
    assert len(db_session.statements) == 1


def test_list_shelters_supports_region_filter(db_session: _FakeSession) -> None:
    response = client.get("/api/shelters", params={"region_id": 7})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 11,
            "name": "Example shelter",
            "region_id": 7,
            "capacity": 120,
            "current_occupancy": 18,
            "source_name": "Example municipal dataset",
            "source_reference": "shelter 11",
            "source_license": None,
            "verification_status": "unverified",
            "verified_at": None,
            "verified_by": None,
            "location": {"type": "Point", "coordinates": [86.5, 25.5]},
        }
    ]
    assert "shelters.region_id =" in str(db_session.statements[0])


def test_catalog_endpoints_return_empty_lists(db_session: _FakeSession) -> None:
    db_session.empty = True

    assert client.get("/api/regions").json() == []
    assert client.get("/api/shelters").json() == []


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        ("/api/regions", "Unable to retrieve regions from the database"),
        ("/api/shelters", "Unable to retrieve shelters from the database"),
    ],
)
def test_catalog_endpoints_report_database_errors(
    db_session: _FakeSession, path: str, detail: str
) -> None:
    db_session.fail = True

    response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {"detail": detail}
