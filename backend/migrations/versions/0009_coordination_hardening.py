"""Harden supply coordination lifecycle and public submission throttling.

Revision ID: 0009_coordination_hardening
Revises: 0008_supply_coordination
Create Date: 2026-11-22
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_coordination_hardening"
down_revision: str | None = "0008_supply_coordination"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist moderation, actual pickup, cancellation, and shared rate limits."""
    op.create_index(
        "idx_supply_offers_pickup_point",
        "supply_offers",
        ["pickup_point"],
        postgresql_using="gist",
    )
    op.add_column("help_requests", sa.Column("moderation_reason", sa.String(length=16)))
    op.add_column(
        "help_requests",
        sa.Column(
            "moderated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
    )
    op.add_column("help_requests", sa.Column("moderated_at", sa.DateTime(timezone=True)))
    op.add_column(
        "help_requests",
        sa.Column(
            "closed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
    )
    op.add_column("help_requests", sa.Column("closed_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_help_requests_moderation_reason",
        "help_requests",
        "moderation_reason IS NULL OR moderation_reason IN ('spam', 'duplicate')",
    )

    op.add_column("supply_offers", sa.Column("actual_units_picked_up", sa.Integer()))
    op.add_column("supply_offers", sa.Column("cancelled_at", sa.DateTime(timezone=True)))
    op.add_column("supply_offers", sa.Column("cancellation_reason", sa.String(length=32)))
    op.add_column(
        "supply_offers",
        sa.Column(
            "cancelled_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
    )
    op.drop_constraint("ck_supply_offers_status", "supply_offers", type_="check")
    op.create_check_constraint(
        "ck_supply_offers_status",
        "supply_offers",
        "status IN ('pending_responder', 'responder_assigned', 'contacted', "
        "'picked_up', 'delivered', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_supply_offers_actual_units_picked_up",
        "supply_offers",
        "actual_units_picked_up IS NULL OR "
        "(actual_units_picked_up >= 0 AND actual_units_picked_up <= units_offered)",
    )
    op.create_table(
        "coordination_rate_limits",
        sa.Column("bucket_key", sa.String(length=300), primary_key=True),
        sa.Column("available_tokens", sa.Float(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_coordination_rate_limits_updated_at",
        "coordination_rate_limits",
        ["updated_at"],
    )


def downgrade() -> None:
    """Remove hardening columns and the shared rate-limit table."""
    op.drop_index(
        "ix_coordination_rate_limits_updated_at",
        table_name="coordination_rate_limits",
    )
    op.drop_table("coordination_rate_limits")
    op.drop_index("idx_supply_offers_pickup_point", table_name="supply_offers")
    op.drop_constraint("ck_supply_offers_actual_units_picked_up", "supply_offers", type_="check")
    op.drop_constraint("ck_supply_offers_status", "supply_offers", type_="check")
    op.create_check_constraint(
        "ck_supply_offers_status",
        "supply_offers",
        "status IN ('pending_responder', 'responder_assigned', 'contacted', "
        "'picked_up', 'delivered')",
    )
    op.drop_column("supply_offers", "cancelled_by_user_id")
    op.drop_column("supply_offers", "cancellation_reason")
    op.drop_column("supply_offers", "cancelled_at")
    op.drop_column("supply_offers", "actual_units_picked_up")

    op.drop_constraint("ck_help_requests_moderation_reason", "help_requests", type_="check")
    op.drop_column("help_requests", "closed_at")
    op.drop_column("help_requests", "closed_by_user_id")
    op.drop_column("help_requests", "moderated_at")
    op.drop_column("help_requests", "moderated_by_user_id")
    op.drop_column("help_requests", "moderation_reason")
