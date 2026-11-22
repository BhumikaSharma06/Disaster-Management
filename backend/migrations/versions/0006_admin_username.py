"""Add usernames for username-based administrator sign-in.

Revision ID: 0006_admin_username
Revises: 0005_responder_approval
Create Date: 2026-11-22
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_admin_username"
down_revision: str | None = "0005_responder_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add an optional unique username, populated for bootstrapped admins."""
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_users_username", "users", ["username"])


def downgrade() -> None:
    """Remove usernames."""
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
