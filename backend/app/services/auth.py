"""Password hashing, email-token hashing, and JWT access-token helpers."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.models.user import User

_password_hash = PasswordHash.recommended()
_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Create an Argon2 password hash."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its Argon2 hash."""
    return _password_hash.verify(password, password_hash)


def create_verification_token() -> tuple[str, str, datetime]:
    """Return a random raw email token, its digest, and its expiry."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.email_verification_token_minutes)
    return token, token_hash, expires_at


def hash_verification_token(token: str) -> str:
    """Hash a presented verification token for database lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user: User) -> str:
    """Issue a short-lived signed bearer token for an authenticated user."""
    if len(settings.auth_jwt_secret) < 32:
        raise RuntimeError("AUTH_JWT_SECRET must contain at least 32 characters")
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "token_version": user.auth_token_version or 0,
            "iat": now,
            "exp": now + timedelta(minutes=settings.auth_access_token_minutes),
        },
        settings.auth_jwt_secret,
        algorithm=_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> tuple[UUID, int]:
    """Validate a bearer token and return its user identifier and version."""
    if len(settings.auth_jwt_secret) < 32:
        raise RuntimeError("AUTH_JWT_SECRET must contain at least 32 characters")
    payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=[_JWT_ALGORITHM])
    return UUID(payload["sub"]), int(payload.get("token_version", 0))
