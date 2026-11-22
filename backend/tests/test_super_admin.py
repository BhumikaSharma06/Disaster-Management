"""Tests for Super Administrator simulation and audit controls."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.admin_audit import AdminAuditLog
from app.models.disaster_simulation import DisasterSimulation
from app.models.user import User


@pytest.fixture
def super_admin_environment():
    """Provide an isolated database and switchable authenticated user."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    AdminAuditLog.__table__.create(engine)
    DisasterSimulation.__table__.create(engine)
    test_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    super_admin = User(
        id=uuid.uuid4(),
        full_name="Super Administrator",
        email="super-admin@example.test",
        password_hash="test-hash",
        is_admin=True,
        is_super_admin=True,
        is_email_verified=True,
    )
    normal_admin = User(
        id=uuid.uuid4(),
        full_name="Administrator",
        email="admin@example.test",
        password_hash="test-hash",
        is_admin=True,
        is_email_verified=True,
    )
    with test_session() as db:
        db.add_all([super_admin, normal_admin])
        db.commit()
    authenticated_user = [super_admin]

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: authenticated_user[0]
    client = TestClient(app)
    try:
        yield client, test_session, authenticated_user, super_admin, normal_admin
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        engine.dispose()


def test_super_admin_simulation_lifecycle_is_isolated_and_audited(
    super_admin_environment,
) -> None:
    client, test_session, _, super_admin, _ = super_admin_environment
    payload = {
        "name": "Regional flood exercise",
        "hazard_type": "flood",
        "area_name": "Example district",
        "severity": "high",
        "scenario_notes": "Tabletop validation only.",
    }

    started = client.post("/api/v1/super-admin/simulations", json=payload)

    assert started.status_code == 201
    simulation = started.json()
    assert simulation["status"] == "running"
    assert simulation["started_by_user_id"] == str(super_admin.id)
    assert client.post("/api/v1/super-admin/simulations", json=payload).status_code == 409

    stopped = client.post(f"/api/v1/super-admin/simulations/{simulation['id']}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["ended_at"] is not None
    assert client.post(f"/api/v1/super-admin/simulations/{simulation['id']}/stop").status_code == 409

    listed = client.get("/api/v1/super-admin/simulations")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    logs = client.get("/api/v1/super-admin/audit-logs")
    assert logs.status_code == 200
    assert [entry["action"] for entry in logs.json()] == [
        "simulation_stopped",
        "simulation_started",
    ]
    with test_session() as db:
        assert len(db.scalars(select(DisasterSimulation)).all()) == 1
        assert len(db.scalars(select(AdminAuditLog)).all()) == 2


def test_administrator_cannot_access_super_admin_controls(super_admin_environment) -> None:
    client, _, authenticated_user, _, normal_admin = super_admin_environment
    authenticated_user[0] = normal_admin

    assert client.get("/api/v1/super-admin/simulations").status_code == 403
    assert client.get("/api/v1/super-admin/audit-logs").status_code == 403
    assert client.post(
        "/api/v1/super-admin/simulations",
        json={
            "name": "Unauthorized scenario",
            "hazard_type": "flood",
            "area_name": "Example district",
            "severity": "moderate",
        },
    ).status_code == 403
