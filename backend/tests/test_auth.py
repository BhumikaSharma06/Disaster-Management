"""Authentication, verification, and role-access API tests."""

import asyncio
import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.user import User
from app.models.admin_audit import AdminAuditLog
from app.services import auth as auth_service
from app.services import bootstrap_admin
from app.services import email as email_service


@pytest.fixture
def auth_test_environment(monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated SQLite user table and a captured verification sender."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    AdminAuditLog.__table__.create(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sent_tokens: list[tuple[str, str, str]] = []

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    async def capture_email(email: str, full_name: str, token: str) -> None:
        sent_tokens.append((email, full_name, token))

    monkeypatch.setattr(auth_service, "settings", replace(settings, auth_jwt_secret="x" * 48))
    monkeypatch.setattr("app.api.auth.send_verification_email", capture_email)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, test_session, sent_tokens
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def register(client: TestClient, email: str, **fields) -> dict:
    """Register a user and return the JSON payload."""
    return client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "AapdaSetu Tester",
            "email": email,
            "password": "secure-test-password",
            **fields,
        },
    ).json()


def test_registration_defaults_to_community_user(auth_test_environment) -> None:
    client, test_session, sent_tokens = auth_test_environment
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Community User",
            "email": "Citizen@Example.test",
            "password": "secure-test-password",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "citizen@example.test"
    assert len(sent_tokens) == 1
    with test_session() as db:
        user = db.scalar(select(User).where(User.email == "citizen@example.test"))
        assert user is not None
        assert user.is_responder is False
        assert user.is_admin is False
        assert user.is_email_verified is False
        assert user.password_hash != "secure-test-password"
        assert (
            user.email_verification_token_hash
            == hashlib.sha256(sent_tokens[0][2].encode()).hexdigest()
        )


def test_registration_accepts_responder_profile(auth_test_environment) -> None:
    client, test_session, _ = auth_test_environment
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Responder User",
            "email": "responder@example.test",
            "password": "secure-test-password",
            "is_responder": True,
            "responder_unit": "Community Response Team",
            "responder_phone": "+911234567890",
        },
    )

    assert response.status_code == 201
    with test_session() as db:
        user = db.scalar(select(User).where(User.email == "responder@example.test"))
        assert user is not None
        assert user.is_responder is False
        assert user.responder_request_status == "pending"
        assert user.responder_unit == "Community Response Team"
        assert user.responder_phone == "+911234567890"


def test_registration_cannot_assign_admin_role(auth_test_environment) -> None:
    client, test_session, _ = auth_test_environment
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Untrusted Admin",
            "email": "untrusted-admin@example.test",
            "password": "secure-test-password",
            "is_admin": True,
        },
    )

    assert response.status_code == 422
    with test_session() as db:
        assert (
            db.scalar(select(User.id).where(User.email == "untrusted-admin@example.test")) is None
        )


def test_unverified_user_cannot_login_and_can_verify(auth_test_environment) -> None:
    client, test_session, sent_tokens = auth_test_environment
    register(client, "verify@example.test")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "verify@example.test", "password": "secure-test-password"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "email_not_verified"
    token = sent_tokens[0][2]
    verified = client.get("/api/v1/auth/verify-email", params={"token": token})
    assert verified.status_code == 200
    assert verified.json()["is_email_verified"] is True

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "verify@example.test", "password": "secure-test-password"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "verify@example.test"
    assert login_response.json()["user"]["is_email_verified"] is True
    assert login_response.json()["access_token"]
    with test_session() as db:
        user = db.scalar(select(User).where(User.email == "verify@example.test"))
        assert user is not None
        assert user.email_verification_token_hash is None


def test_admin_can_login_case_insensitively_by_username_or_email_and_logout(
    auth_test_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, test_session, _ = auth_test_environment
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", test_session)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_FULL_NAME", "Bootstrap Administrator")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "RegionalAdmin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "regionaladmin@example.test")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "long-local-admin-password")
    monkeypatch.setenv("AUTH_JWT_SECRET", "s" * 48)
    assert bootstrap_admin.main() == 0

    username_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "RegionalAdmin", "password": "long-local-admin-password"},
    )
    email_login = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "REGIONALADMIN@EXAMPLE.TEST",
            "password": "long-local-admin-password",
        },
    )

    assert username_login.status_code == 200
    assert username_login.json()["user"]["is_admin"] is True
    assert email_login.status_code == 200
    assert email_login.json()["user"]["is_admin"] is True

    headers = {"Authorization": f"Bearer {username_login.json()['access_token']}"}
    logged_out = client.post("/api/v1/auth/logout", headers=headers)
    assert logged_out.status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
        ).status_code
        == 401
    )


def test_login_rejects_invalid_credentials_with_visible_error_detail(auth_test_environment) -> None:
    client, _, _ = auth_test_environment
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "unknown@example.test", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Username/email or password is incorrect."


def test_resend_rotates_verification_token(auth_test_environment) -> None:
    client, _, sent_tokens = auth_test_environment
    register(client, "resend@example.test")
    original_token = sent_tokens[0][2]
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "RESEND@example.test"},
    )

    assert response.status_code == 200
    assert len(sent_tokens) == 2
    assert (
        client.post("/api/v1/auth/verify-email", json={"token": original_token}).status_code == 400
    )
    assert (
        client.post("/api/v1/auth/verify-email", json={"token": sent_tokens[1][2]}).status_code
        == 200
    )


def test_expired_verification_link_is_rejected(auth_test_environment) -> None:
    client, test_session, sent_tokens = auth_test_environment
    register(client, "expired@example.test")
    with test_session() as db:
        user = db.scalar(select(User).where(User.email == "expired@example.test"))
        assert user is not None
        user.verification_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": sent_tokens[0][2]},
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


def test_role_routes_require_verified_role(auth_test_environment) -> None:
    client, _, sent_tokens = auth_test_environment
    register(client, "community@example.test")
    client.post("/api/v1/auth/verify-email", json={"token": sent_tokens[0][2]})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "community@example.test", "password": "secure-test-password"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/responder/profile", headers=headers).status_code == 403
    assert client.get("/api/v1/auth/admin/users", headers=headers).status_code == 403
    assert client.get("/api/v1/coordination/inbox-count", headers=headers).status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/coordination/inbox-count").status_code == 401


def test_authenticated_user_can_update_and_clear_saved_profile_details(
    auth_test_environment,
) -> None:
    client, _, sent_tokens = auth_test_environment
    register(client, "profile@example.test")
    client.post("/api/v1/auth/verify-email", json={"token": sent_tokens[0][2]})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "profile@example.test", "password": "secure-test-password"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "contact_phone": " +911234567890 ",
            "home_state": " Example State ",
            "home_district": "Example District",
            "home_locality": "Example Ward",
            "home_landmark": "Near the community centre",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["contact_phone"] == "+911234567890"
    assert updated.json()["home_state"] == "Example State"
    assert updated.json()["home_district"] == "Example District"
    assert updated.json()["home_locality"] == "Example Ward"
    assert updated.json()["home_landmark"] == "Near the community centre"
    assert client.get("/api/v1/auth/me", headers=headers).json()["home_locality"] == "Example Ward"

    cleared = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"contact_phone": None, "home_landmark": "  "},
    )
    assert cleared.status_code == 200
    assert cleared.json()["contact_phone"] is None
    assert cleared.json()["home_landmark"] is None
    assert cleared.json()["home_state"] == "Example State"


def test_profile_update_requires_authentication_and_valid_contact_phone(
    auth_test_environment,
) -> None:
    client, _, sent_tokens = auth_test_environment
    register(client, "profile-validation@example.test")
    client.post("/api/v1/auth/verify-email", json={"token": sent_tokens[0][2]})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "profile-validation@example.test", "password": "secure-test-password"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    assert client.patch("/api/v1/auth/me", json={"home_state": "Example State"}).status_code == 401
    invalid_phone = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"contact_phone": "not-a-phone"},
    )
    assert invalid_phone.status_code == 422


def test_responder_and_admin_roles_can_access_protected_routes(auth_test_environment) -> None:
    client, test_session, sent_tokens = auth_test_environment
    register(
        client,
        "responder@example.test",
        is_responder=True,
        responder_unit="Response Team",
    )
    register(client, "admin@example.test")
    with test_session() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.test"))
        assert admin is not None
        admin.is_admin = True
        admin.username = "adminoperator"
        responder = db.scalar(select(User).where(User.email == "responder@example.test"))
        assert responder is not None
        responder_id = responder.id
        db.commit()

    responder_verified = client.post(
        "/api/v1/auth/verify-email",
        json={"token": sent_tokens[0][2]},
    )
    admin_verified = client.post(
        "/api/v1/auth/verify-email",
        json={"token": sent_tokens[1][2]},
    )
    assert responder_verified.status_code == admin_verified.status_code == 200

    responder_login = client.post(
        "/api/v1/auth/login",
        json={"email": "responder@example.test", "password": "secure-test-password"},
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "AdminOperator", "password": "secure-test-password"},
    )
    admin_email_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "secure-test-password"},
    )
    assert admin_email_login.status_code == 200
    assert admin_email_login.json()["user"]["is_admin"] is True
    responder_headers = {"Authorization": f"Bearer {responder_login.json()['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    approval = client.post(
        f"/api/v1/auth/admin/responder-requests/{responder_id}/decision",
        headers=admin_headers,
        json={"decision": "approve"},
    )
    assert approval.status_code == 200
    with test_session() as db:
        audit = db.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "responder_request_approved"))
        assert audit is not None
        assert audit.target_id == str(responder_id)
    profile = client.get("/api/v1/auth/responder/profile", headers=responder_headers)
    assert profile.status_code == 200
    assert profile.json()["responder_unit"] == "Response Team"
    admin_users = client.get("/api/v1/auth/admin/users", headers=admin_headers)
    assert admin_users.status_code == 200
    assert {user["email"] for user in admin_users.json()} == {
        "responder@example.test",
        "admin@example.test",
    }
    assert all("contact_phone" not in user for user in admin_users.json())
    assert all("home_state" not in user for user in admin_users.json())


def test_admin_approval_grants_responder_only_after_email_verification(
    auth_test_environment,
) -> None:
    client, test_session, sent_tokens = auth_test_environment
    register(
        client,
        "pending-responder@example.test",
        is_responder=True,
        responder_unit="District Response Unit",
        responder_phone="1234567890",
    )
    register(client, "verified-admin@example.test")
    with test_session() as db:
        admin = db.scalar(select(User).where(User.email == "verified-admin@example.test"))
        assert admin is not None
        admin.is_admin = True
        admin.username = "verifiedadmin"
        admin.is_email_verified = True
        db.commit()
        responder = db.scalar(select(User).where(User.email == "pending-responder@example.test"))
        assert responder is not None
        responder_id = responder.id

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "verifiedadmin", "password": "secure-test-password"},
    )
    headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    pending = client.get("/api/v1/auth/admin/responder-requests", headers=headers)
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    assert pending.json()[0]["is_responder"] is False
    approval = client.post(
        f"/api/v1/auth/admin/responder-requests/{responder_id}/decision",
        headers=headers,
        json={"decision": "approve"},
    )
    assert approval.status_code == 409

    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"token": sent_tokens[0][2]},
    )
    assert verified.status_code == 200
    approval = client.post(
        f"/api/v1/auth/admin/responder-requests/{responder_id}/decision",
        headers=headers,
        json={"decision": "approve"},
    )
    assert approval.status_code == 200
    assert approval.json()["is_responder"] is True
    assert approval.json()["responder_request_status"] == "approved"

    responder_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "pending-responder@example.test",
            "password": "secure-test-password",
        },
    )
    responder_headers = {"Authorization": f"Bearer {responder_login.json()['access_token']}"}
    assert (
        client.get("/api/v1/auth/responder/profile", headers=responder_headers).status_code == 200
    )


def test_admin_can_reject_responder_request_and_user_remains_community(
    auth_test_environment,
) -> None:
    client, test_session, sent_tokens = auth_test_environment
    register(
        client,
        "requester@example.test",
        is_responder=True,
        responder_unit="Community response group",
    )
    register(client, "reviewer@example.test")
    with test_session() as db:
        admin = db.scalar(select(User).where(User.email == "reviewer@example.test"))
        assert admin is not None
        admin.is_admin = True
        admin.username = "reviewer"
        admin.is_email_verified = True
        db.commit()
        requester = db.scalar(select(User).where(User.email == "requester@example.test"))
        assert requester is not None
        requester_id = requester.id

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "reviewer", "password": "secure-test-password"},
    )
    headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    client.post("/api/v1/auth/verify-email", json={"token": sent_tokens[0][2]})
    rejected = client.post(
        f"/api/v1/auth/admin/responder-requests/{requester_id}/decision",
        headers=headers,
        json={"decision": "reject"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["is_responder"] is False
    assert rejected.json()["responder_request_status"] == "rejected"
    with test_session() as db:
        audit = db.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "responder_request_rejected"))
        assert audit is not None
    assert rejected.json()["responder_unit"] == "Community response group"

    client.post("/api/v1/auth/verify-email", json={"token": sent_tokens[0][2]})
    requester_login = client.post(
        "/api/v1/auth/login",
        json={"email": "requester@example.test", "password": "secure-test-password"},
    )
    requester_headers = {"Authorization": f"Bearer {requester_login.json()['access_token']}"}
    new_request = client.post(
        "/api/v1/auth/responder/request",
        headers=requester_headers,
    )
    assert new_request.status_code == 200
    assert new_request.json()["is_responder"] is False
    assert new_request.json()["responder_request_status"] == "pending"


def test_bootstrap_admin_creates_verified_admin_from_explicit_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_users: list[User] = []

    class BootstrapSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def scalar(self, _statement):
            return None

        def add(self, user: User) -> None:
            created_users.append(user)

        def commit(self) -> None:
            return None

    monkeypatch.setattr(bootstrap_admin, "SessionLocal", BootstrapSession)
    monkeypatch.setattr(bootstrap_admin, "hash_password", lambda password: f"hashed:{password}")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_FULL_NAME", "Local Admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "LocalAdmin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "ADMIN@example.test")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "long-local-admin-password")
    monkeypatch.setenv("AUTH_JWT_SECRET", "s" * 48)

    assert bootstrap_admin.main() == 0
    assert len(created_users) == 1
    assert created_users[0].email == "admin@example.test"
    assert created_users[0].username == "localadmin"
    assert created_users[0].is_admin is True
    assert created_users[0].is_email_verified is True
    assert created_users[0].is_responder is False
    assert created_users[0].password_hash == "hashed:long-local-admin-password"


def test_bootstrap_admin_adds_username_to_existing_admin(
    auth_test_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, test_session, _ = auth_test_environment
    with test_session() as db:
        admin = User(
            full_name="Existing Admin",
            email="existing-admin@example.test",
            password_hash="already-hashed",
            is_admin=True,
            is_email_verified=True,
        )
        db.add(admin)
        db.commit()

    monkeypatch.setattr(bootstrap_admin, "SessionLocal", test_session)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_FULL_NAME", "Existing Admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "existingadmin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "existing-admin@example.test")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "long-local-admin-password")
    monkeypatch.setenv("AUTH_JWT_SECRET", "s" * 48)

    assert bootstrap_admin.main() == 0
    with test_session() as db:
        admin = db.scalar(select(User).where(User.email == "existing-admin@example.test"))
        assert admin is not None
        assert admin.username == "existingadmin"
        assert admin.password_hash == "already-hashed"


def test_verification_email_smtp_dispatch_is_async_and_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: dict = {}

    async def fake_send(message, **kwargs) -> None:
        sent["message"] = message
        sent["kwargs"] = kwargs

    monkeypatch.setattr(
        email_service,
        "settings",
        replace(
            settings,
            smtp_host="mailpit",
            smtp_port=1025,
            frontend_base_url="http://localhost:5173",
            email_verification_token_minutes=1440,
        ),
    )
    monkeypatch.setattr(email_service.aiosmtplib, "send", fake_send)

    asyncio.run(
        email_service.send_verification_email(
            "member@example.test", "Test Member", "test-token-value"
        )
    )

    assert sent["kwargs"]["hostname"] == "mailpit"
    assert sent["kwargs"]["port"] == 1025
    assert "test-token-value" in sent["message"].get_body(preferencelist=("plain",)).get_content()
    assert sent["message"]["To"] == "member@example.test"
