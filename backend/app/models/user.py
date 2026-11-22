"""User accounts and email-verification state."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """A registered community account or approved responder account."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint(
            "email_verification_token_hash",
            name="uq_users_email_verification_token_hash",
        ),
        CheckConstraint(
            "responder_request_status IN ('not_requested', 'pending', 'approved', 'rejected')",
            name="ck_users_responder_request_status",
        ),
        CheckConstraint(
            "(responder_request_status = 'approved' AND is_responder) OR "
            "(responder_request_status <> 'approved' AND NOT is_responder)",
            name="ck_users_responder_approval",
        ),
        CheckConstraint(
            "NOT is_super_admin OR is_admin",
            name="ck_users_super_admin_is_admin",
        ),
        Index("ix_users_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    username: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_responder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    responder_request_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_requested", server_default="not_requested"
    )
    responder_unit: Mapped[str | None] = mapped_column(String(160))
    responder_phone: Mapped[str | None] = mapped_column(String(40))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    home_state: Mapped[str | None] = mapped_column(String(120))
    home_district: Mapped[str | None] = mapped_column(String(120))
    home_locality: Mapped[str | None] = mapped_column(String(200))
    home_landmark: Mapped[str | None] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auth_token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    email_verification_token_hash: Mapped[str | None] = mapped_column(String(64))
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
