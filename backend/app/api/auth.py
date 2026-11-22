"""Account registration, email verification, login, and role-protected routes."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import aiosmtplib
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.admin_audit import record_admin_action
from app.schemas.auth import (
    AccountProfileResponse,
    AdminRoleUpdateRequest,
    AdminUserResponse,
    EmailRequest,
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
    RegistrationRequest,
    RegistrationResponse,
    ResponderApprovalRequest,
    ResponderProfileResponse,
    VerificationResponse,
    VerifyEmailRequest,
)
from app.services.auth import (
    create_access_token,
    create_verification_token,
    decode_access_token,
    hash_password,
    hash_verification_token,
    verify_password,
)
from app.services.email import send_verification_email

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_db)]


def _smtp_unavailable() -> HTTPException:
    """Create the public service error used when SMTP delivery fails."""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The verification email could not be sent. Please try again.",
    )


async def _deliver_verification(user: User, token: str) -> None:
    """Send a verification message and report relay errors explicitly."""
    try:
        await send_verification_email(user.email, user.full_name, token)
    except (aiosmtplib.SMTPException, OSError, asyncio.TimeoutError) as error:
        raise _smtp_unavailable() from error


@router.post("/register", response_model=RegistrationResponse, status_code=201)
async def register(payload: RegistrationRequest, db: DatabaseSession) -> RegistrationResponse:
    """Create an unverified user and send a one-time email-verification link."""
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    token, token_hash, expires_at = create_verification_token()
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=await asyncio.to_thread(hash_password, payload.password),
        is_responder=False,
        responder_request_status="pending" if payload.is_responder else "not_requested",
        responder_unit=payload.responder_unit if payload.is_responder else None,
        responder_phone=payload.responder_phone if payload.is_responder else None,
        is_email_verified=False,
        email_verification_token_hash=token_hash,
        verification_token_expires_at=expires_at,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from error
    db.refresh(user)
    await _deliver_verification(user, token)
    return RegistrationResponse(
        message="Account created. Check your email to verify it before signing in.",
        email=user.email,
        mailpit_ui_url=settings.mailpit_ui_url,
    )


def _verify_token(token: str, db: Session) -> VerificationResponse:
    """Verify an unexpired email token and consume it."""
    user = db.scalar(
        select(User).where(User.email_verification_token_hash == hash_verification_token(token))
    )
    if user is None or user.verification_token_expires_at is None:
        raise HTTPException(status_code=400, detail="Verification link is invalid or expired.")

    expires_at = user.verification_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=400,
            detail="Verification link is expired. Request a new verification email.",
        )

    user.is_email_verified = True
    user.email_verification_token_hash = None
    user.verification_token_expires_at = None
    db.commit()
    return VerificationResponse(
        message="Email verified. You can now sign in.",
        is_email_verified=True,
    )


@router.get("/verify-email", response_model=VerificationResponse)
def verify_email_get(
    db: DatabaseSession,
    token: str = Query(min_length=20, max_length=200),
) -> VerificationResponse:
    """Verify an email from a clickable link."""
    return _verify_token(token, db)


@router.post("/verify-email", response_model=VerificationResponse)
def verify_email_post(payload: VerifyEmailRequest, db: DatabaseSession) -> VerificationResponse:
    """Verify an email from the frontend form."""
    return _verify_token(payload.token, db)


@router.post("/resend-verification", response_model=RegistrationResponse)
async def resend_verification(payload: EmailRequest, db: DatabaseSession) -> RegistrationResponse:
    """Rotate and resend a verification link without disclosing account existence."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None and not user.is_email_verified:
        token, token_hash, expires_at = create_verification_token()
        user.email_verification_token_hash = token_hash
        user.verification_token_expires_at = expires_at
        db.commit()
        await _deliver_verification(user, token)

    return RegistrationResponse(
        message="If an unverified account exists for that email, a new link has been sent.",
        email=payload.email,
        mailpit_ui_url=settings.mailpit_ui_url,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DatabaseSession) -> LoginResponse:
    """Authenticate a verified user and return a short-lived access token."""
    identifier = payload.identifier
    password = payload.password
    user = db.scalar(
        select(User).where(
            (func.lower(User.email) == identifier) | (func.lower(User.username) == identifier)
        )
    )
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deleted.",
        )
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Verify your email before signing in.",
            },
        )
    try:
        token = create_access_token(user)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured. Set AUTH_JWT_SECRET.",
        ) from error
    return LoginResponse(access_token=token, user=AccountProfileResponse.model_validate(user))


def _resolve_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: DatabaseSession,
) -> User | None:
    """Resolve an optional bearer token, rejecting invalid supplied credentials."""
    if credentials is None:
        return None
    try:
        user_id, token_version = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is invalid or expired. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_version != user.auth_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is no longer valid. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before accessing this resource.",
        )
    return user


def get_optional_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: DatabaseSession,
) -> User | None:
    """Resolve the current user when a valid bearer token is supplied."""
    return _resolve_current_user(credentials, db)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: DatabaseSession,
) -> User:
    """Resolve the current authenticated and verified user."""
    user = _resolve_current_user(credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_responder(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require a verified account marked as a responder."""
    if not user.is_responder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified responder account is required for this action.",
        )
    return user


def require_responder_or_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require a verified responder or administrator account."""
    if not user.is_responder and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Responder or administrator access is required for this action.",
        )
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require a verified administrator account."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required for this action.",
        )
    return user


def require_super_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require the bootstrap or assigned Super Administrator role."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Administrator access is required for this action.",
        )
    return user


@router.get("/me", response_model=AccountProfileResponse)
def current_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Return the authenticated user's safe public profile."""
    return user


@router.patch("/me", response_model=AccountProfileResponse)
def update_current_user(
    payload: ProfileUpdateRequest,
    db: DatabaseSession,
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Update the authenticated user's optional contact and saved-address details."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: DatabaseSession,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Invalidate the user's current and previously issued access tokens."""
    user.auth_token_version += 1
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/responder/profile", response_model=ResponderProfileResponse)
def responder_profile(user: Annotated[User, Depends(require_responder)]) -> User:
    """Return responder-only account details."""
    return user


@router.post("/responder/request", response_model=AccountProfileResponse)
def request_responder_role(
    db: DatabaseSession,
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Submit or renew a responder-role request for admin review."""
    if user.is_responder:
        raise HTTPException(
            status_code=409,
            detail="This account already has responder access.",
        )
    if user.responder_request_status == "pending":
        raise HTTPException(
            status_code=409,
            detail="A responder-role request is already awaiting review.",
        )
    user.responder_request_status = "pending"
    db.commit()
    db.refresh(user)
    return user


@router.get("/admin/users", response_model=list[AdminUserResponse])
def admin_users(
    db: DatabaseSession,
    admin: Annotated[User, Depends(require_admin)],
) -> list[User]:
    """List account and role metadata for verified administrators."""
    del admin
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@router.delete("/admin/users/{user_id}", response_model=AdminUserResponse)
def delete_admin_user(
    user_id: UUID,
    db: DatabaseSession,
    admin: Annotated[User, Depends(require_admin)],
) -> User:
    """Soft-delete a registered account and invalidate its current sessions."""
    if admin.id == user_id:
        raise HTTPException(status_code=409, detail="The signed-in administrator cannot delete their own account.")
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="This account is already deleted.")
    if user.is_admin:
        raise HTTPException(status_code=409, detail="Administrator accounts cannot be deleted from the account directory.")
    user.deleted_at = datetime.now(UTC)
    user.is_responder = False
    user.responder_request_status = "not_requested"
    user.auth_token_version += 1
    record_admin_action(
        db,
        admin,
        action="account_deleted",
        target_type="user",
        target_id=str(user.id),
        target_label=user.email,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/admin/users/{user_id}/restore", response_model=AdminUserResponse)
def restore_admin_user(
    user_id: UUID,
    db: DatabaseSession,
    admin: Annotated[User, Depends(require_admin)],
) -> User:
    """Restore a previously soft-deleted community or responder account."""
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if user.deleted_at is None:
        raise HTTPException(status_code=409, detail="This account is not deleted.")
    user.deleted_at = None
    record_admin_action(
        db,
        admin,
        action="account_restored",
        target_type="user",
        target_id=str(user.id),
        target_label=user.email,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/admin/users/{user_id}/role", response_model=AdminUserResponse)
def update_admin_role(
    user_id: UUID,
    payload: AdminRoleUpdateRequest,
    db: DatabaseSession,
    super_admin: Annotated[User, Depends(require_super_admin)],
) -> User:
    """Promote or demote a verified normal account as an Administrator."""
    if super_admin.id == user_id:
        raise HTTPException(status_code=409, detail="The Super Administrator role cannot be changed through this action.")
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Restore the account before changing its role.")

    if payload.decision == "promote":
        if not user.is_email_verified:
            raise HTTPException(status_code=409, detail="The account must verify email before Administrator promotion.")
        if user.is_super_admin:
            raise HTTPException(status_code=409, detail="The account is already a Super Administrator.")
        user.is_admin = True
    else:
        if not user.is_admin:
            raise HTTPException(status_code=409, detail="The account is not an Administrator.")
        if user.is_super_admin:
            raise HTTPException(status_code=409, detail="The Super Administrator role cannot be demoted here.")
        user.is_admin = False
        user.is_responder = False
        user.responder_request_status = "not_requested"
    user.auth_token_version += 1
    record_admin_action(
        db,
        super_admin,
        action="admin_promoted" if payload.decision == "promote" else "admin_demoted",
        target_type="user",
        target_id=str(user.id),
        target_label=user.email,
        details={"is_admin": user.is_admin},
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/admin/responder-requests", response_model=list[AdminUserResponse])
def admin_responder_requests(
    db: DatabaseSession,
    admin: Annotated[User, Depends(require_admin)],
) -> list[User]:
    """List users awaiting admin review for responder access."""
    del admin
    return list(
        db.scalars(
            select(User)
            .where(User.responder_request_status == "pending")
            .order_by(User.created_at.asc())
        ).all()
    )


@router.post(
    "/admin/responder-requests/{user_id}/decision",
    response_model=AdminUserResponse,
)
def decide_responder_request(
    user_id: UUID,
    payload: ResponderApprovalRequest,
    db: DatabaseSession,
    admin: Annotated[User, Depends(require_admin)],
) -> User:
    """Approve or reject a pending responder-role request."""
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if user.responder_request_status != "pending":
        raise HTTPException(
            status_code=409,
            detail="This account does not have a pending responder-role request.",
        )

    approved = payload.decision == "approve"
    if approved and not user.is_email_verified:
        raise HTTPException(
            status_code=409,
            detail="The user must verify their email before responder access can be approved.",
        )
    user.is_responder = approved
    user.responder_request_status = "approved" if approved else "rejected"
    record_admin_action(
        db,
        admin,
        action="responder_request_approved" if approved else "responder_request_rejected",
        target_type="user",
        target_id=str(user.id),
        target_label=user.email,
    )
    db.commit()
    db.refresh(user)
    return user
