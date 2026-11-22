"""Associate coordination submissions with optional user accounts."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_coordination_history"
down_revision: str | None = "0011_optional_address"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable owners and a cancelled help-request terminal state."""
    op.add_column(
        "help_requests",
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_help_requests_created_by_user_id",
        "help_requests",
        ["created_by_user_id"],
    )
    op.add_column(
        "supply_offers",
        sa.Column(
            "donor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_supply_offers_donor_user_id", "supply_offers", ["donor_user_id"])
    op.drop_constraint("ck_help_requests_status", "help_requests", type_="check")
    op.create_check_constraint(
        "ck_help_requests_status",
        "help_requests",
        "status IN ('open', 'partially_fulfilled', 'fulfilled', 'closed', 'cancelled')",
    )


def downgrade() -> None:
    """Remove ownership and restore the original request status constraint."""
    op.drop_constraint("ck_help_requests_status", "help_requests", type_="check")
    op.create_check_constraint(
        "ck_help_requests_status",
        "help_requests",
        "status IN ('open', 'partially_fulfilled', 'fulfilled', 'closed')",
    )
    op.drop_index("ix_supply_offers_donor_user_id", table_name="supply_offers")
    op.drop_index("ix_help_requests_created_by_user_id", table_name="help_requests")
    op.drop_column("supply_offers", "donor_user_id")
    op.drop_column("help_requests", "created_by_user_id")
