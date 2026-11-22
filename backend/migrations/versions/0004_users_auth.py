"""Add user accounts, responder roles, and email verification state.

Revision ID: 0004_users_auth
Revises: 0003_dataset_registry
Create Date: 2026-11-22
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_users_auth"
down_revision: str | None = "0003_dataset_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create accounts with secure role and email-verification defaults."""
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_responder", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("responder_unit", sa.String(length=160), nullable=True),
        sa.Column("responder_phone", sa.String(length=40), nullable=True),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True),
        sa.Column("verification_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint(
            "email_verification_token_hash",
            name="uq_users_email_verification_token_hash",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)


def downgrade() -> None:
    """Remove user accounts and authentication fields."""
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
