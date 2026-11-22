"""Add a user token version for server-side logout invalidation.

Revision ID: 0007_auth_token_version
Revises: 0006_admin_username
Create Date: 2026-11-22
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_auth_token_version"
down_revision: str | None = "0006_admin_username"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Initialize existing accounts at token version zero."""
    op.add_column(
        "users",
        sa.Column("auth_token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    """Remove token-version based access-token invalidation."""
    op.drop_column("users", "auth_token_version")
