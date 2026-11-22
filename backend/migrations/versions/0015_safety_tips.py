"""Add admin-managed safety tips."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_safety_tips"
down_revision: str | None = "0014_account_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the safety-tip table and lifecycle constraints."""
    op.create_table(
        "safety_tips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("hazard_type", sa.String(length=64), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("region", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("source", sa.String(length=254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("phase IN ('before', 'during', 'after')", name="ck_safety_tips_phase"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_safety_tips_status"),
    )


def downgrade() -> None:
    """Remove admin-managed safety tips."""
    op.drop_table("safety_tips")
