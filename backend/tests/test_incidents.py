"""Tests for incident-scoped live operations."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.auth import require_admin, require_responder_or_admin
from app.core.database import get_db
from app.main import app
from app.models.incident import Incident, IncidentShelter
from app.models.admin_audit import AdminAuditLog
from app.models.shelter import Shelter
from app.models.sos_request import SOSRequest
from app.models.user import User

client = TestClient(app)


class _FakeSession:
    def __init__(self) -> None:
        self.incidents: list[Incident] = []
        self.sos: list[SOSRequest] = []
        self.shelters: dict[int, Shelter] = {}
        self.incident_shelters: list[IncidentShelter] = []
        self.audit_logs: list[AdminAuditLog] = []
        self.next_id = 1

    def get(self, model: type, object_id: int) -> Any:
        if model is Incident:
            return next((row for row in self.incidents if row.id == object_id), None)
        if model is Shelter:
            return self.shelters.get(object_id)
        return None

    def scalar(self, statement: Any) -> Any:
        entity = statement.column_descriptions[0]["entity"]
        if entity is SOSRequest:
            submission_id = next(
                (
                    value
                    for value in statement.compile().params.values()
                    if isinstance(value, uuid.UUID)
                ),
                None,
            )
            return next(
                (record for record in self.sos if record.client_submission_id == submission_id),
                None,
            )
        if entity is IncidentShelter:
            return next(
                (
                    row
                    for row in self.incident_shelters
                    if row.incident_id in statement.compile().params.values()
                    and row.shelter_id in statement.compile().params.values()
                ),
                None,
            )
        return None

    def scalars(self, statement: Any) -> "_Rows":
        rows = self.incidents
        if "incidents.status !=" in str(statement):
            rows = [incident for incident in rows if incident.status != "closed"]
        return _Rows(rows)

    def add(self, record: Any) -> None:
        record.id = self.next_id
        self.next_id += 1
        now = datetime.now(UTC)
        if isinstance(record, Incident):
            if record.status is None:
                record.status = "active"
            record.created_at = now
            record.updated_at = now
            self.incidents.append(record)
        elif isinstance(record, SOSRequest):
            if record.status is None:
                record.status = "open"
            record.created_at = now
            record.updated_at = now
            self.sos.append(record)
        elif isinstance(record, IncidentShelter):
            record.updated_at = now
            self.incident_shelters.append(record)
        elif isinstance(record, AdminAuditLog):
            self.audit_logs.append(record)

    def commit(self) -> None:
        return None

    def flush(self) -> None:
        return None

    def refresh(self, record: Any) -> None:
        del record

    def rollback(self) -> None:
        return None


class _Rows:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def all(self) -> list[Any]:
        return self.rows


@pytest.fixture
def operator_session(monkeypatch: pytest.MonkeyPatch) -> _FakeSession:
    session = _FakeSession()
    admin = User(id=uuid.uuid4(), is_admin=True, is_responder=False)
    responder = User(id=uuid.uuid4(), is_admin=False, is_responder=True)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[require_responder_or_admin] = lambda: responder
    monkeypatch.setattr("app.api.incidents.enforce_submission_limit", lambda *_args: None)
    yield session
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(require_responder_or_admin, None)


def test_admin_incident_lifecycle_and_open_selector(operator_session: _FakeSession) -> None:
    response = client.post(
        "/api/v1/incidents",
        json={
            "title": "Coastal response",
            "hazard_type": "cyclone",
            "area_name": "Coastal district",
            "description": "Operator opened incident.",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "active"
    assert response.json()["created_at"]
    incident_id = response.json()["id"]
    assert len(operator_session.incidents) == 1
    assert [entry.action for entry in operator_session.audit_logs] == ["incident_created"]

    closed = client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "closed"})
    assert closed.status_code == 200
    assert [entry.action for entry in operator_session.audit_logs] == [
        "incident_created",
        "incident_status_updated",
    ]
    assert client.get("/api/v1/incidents").json() == []
    assert client.get("/api/v1/incidents?include_closed=true").json()[0]["status"] == "closed"


def test_opening_incident_requires_admin(operator_session: _FakeSession) -> None:
    app.dependency_overrides.pop(require_admin, None)

    response = client.post(
        "/api/v1/incidents",
        json={
            "title": "Unauthorized incident",
            "hazard_type": "flood",
            "area_name": "Example area",
        },
    )

    assert response.status_code == 401
    assert operator_session.incidents == []


def test_public_sos_submission_is_idempotent_and_incident_linkable(
    operator_session: _FakeSession,
) -> None:
    operator_session.incidents.append(
        Incident(
            id=12,
            title="Cyclone response",
            hazard_type="cyclone",
            area_name="Coastal area",
            status="active",
            created_by_user_id=uuid.uuid4(),
        )
    )
    submission_id = str(uuid.uuid4())
    payload = {
        "client_submission_id": submission_id,
        "incident_id": 12,
        "need_type": "medical help",
        "description": "Urgent medical assistance requested.",
        "urgency": "urgent",
        "people_affected": 2,
        "latitude": 19.1,
        "longitude": 72.8,
    }

    first = client.post("/api/v1/sos", json=payload)
    retry = client.post("/api/v1/sos", json=payload)

    assert first.status_code == 201
    assert first.json()["id"] == 1
    assert first.json()["status"] == "open"
    assert retry.json()["id"] == 1
    assert len(operator_session.sos) == 1
    assert operator_session.sos[0].people_affected == 2
    assert operator_session.sos[0].incident_id == 12
    assert operator_session.sos[0].client_submission_id == uuid.UUID(submission_id)


def test_responder_cannot_report_occupancy_above_catalog_capacity(
    operator_session: _FakeSession,
) -> None:
    incident = Incident(
        id=1,
        title="Flood response",
        hazard_type="flood",
        area_name="River district",
        status="active",
        created_by_user_id=uuid.uuid4(),
    )
    operator_session.incidents.append(incident)
    operator_session.shelters[9] = Shelter(id=9, name="Community shelter", capacity=4)

    response = client.put(
        "/api/v1/incidents/1/shelters/9",
        json={
            "operational_status": "open",
            "current_occupancy": 5,
            "update_note": "Operator count",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Reported occupancy cannot exceed")
    assert operator_session.incident_shelters == []


def test_responder_shelter_update_is_audited(operator_session: _FakeSession) -> None:
    operator_session.incidents.append(
        Incident(
            id=1,
            title="Flood response",
            hazard_type="flood",
            area_name="River district",
            status="active",
            created_by_user_id=uuid.uuid4(),
        )
    )
    operator_session.shelters[9] = Shelter(id=9, name="Community shelter", capacity=4)

    response = client.put(
        "/api/v1/incidents/1/shelters/9",
        json={
            "operational_status": "open",
            "current_occupancy": 3,
            "update_note": "Count confirmed by on-site responder.",
        },
    )

    assert response.status_code == 200
    assert response.json()["current_occupancy"] == 3
    assert response.json()["updated_at"]
    assert operator_session.incident_shelters[0].updated_by_user_id
