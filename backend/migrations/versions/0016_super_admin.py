"""Add the bootstrap Super Administrator role."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_super_admin"
down_revision: str | None = "0015_safety_tips"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Super Administrator status and its administrator implication."""
    op.add_column(
        "users",
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        sa.text(
            "UPDATE users SET is_super_admin = true "
            "WHERE id = (SELECT id FROM users WHERE is_admin = true "
            "ORDER BY created_at ASC LIMIT 1)"
        )
    )
    op.create_check_constraint(
        "ck_users_super_admin_is_admin",
        "users",
        "NOT is_super_admin OR is_admin",
    )


def downgrade() -> None:
    """Remove Super Administrator status."""
    op.drop_constraint("ck_users_super_admin_is_admin", "users", type_="check")
    op.drop_column("users", "is_super_admin")
