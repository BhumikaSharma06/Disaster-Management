"""Add reversible account soft deletion."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_account_soft_delete"
down_revision: str | None = "0013_user_contact_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record account deletion without removing coordination evidence."""
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove account soft-deletion state."""
    op.drop_column("users", "deleted_at")
