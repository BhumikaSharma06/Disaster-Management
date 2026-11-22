"""Create persistent help request and supply coordination tables.

Revision ID: 0008_supply_coordination
Revises: 0007_auth_token_version
Create Date: 2026-11-22
"""

from typing import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0008_supply_coordination"
down_revision: str | None = "0007_auth_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add spatial requests, quantity tracking, offers, and responder claims."""
    op.create_table(
        "help_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_submission_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("urgency", sa.String(length=24), nullable=False),
        sa.Column("state", sa.String(length=120), nullable=False),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column("locality", sa.String(length=200), nullable=False),
        sa.Column("landmark", sa.String(length=200)),
        sa.Column("contact_name", sa.String(length=160), nullable=False),
        sa.Column("contact_phone", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('open', 'partially_fulfilled', 'fulfilled', 'closed')",
            name="ck_help_requests_status",
        ),
    )
    op.create_index("ix_help_requests_status", "help_requests", ["status"])
    op.create_index(
        "idx_help_requests_location", "help_requests", ["location"], postgresql_using="gist"
    )

    op.create_table(
        "help_request_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "help_request_id",
            sa.Integer(),
            sa.ForeignKey("help_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_name", sa.String(length=120), nullable=False),
        sa.Column("units_required", sa.Integer(), nullable=False),
        sa.Column("units_fulfilled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_label", sa.String(length=40), nullable=False, server_default="units"),
        sa.CheckConstraint("units_required > 0", name="ck_help_request_items_required_positive"),
        sa.CheckConstraint(
            "units_fulfilled >= 0", name="ck_help_request_items_fulfilled_nonnegative"
        ),
        sa.CheckConstraint(
            "units_fulfilled <= units_required", name="ck_help_request_items_fulfilled_limit"
        ),
    )
    op.create_index(
        "ix_help_request_items_help_request_id", "help_request_items", ["help_request_id"]
    )

    op.create_table(
        "supply_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_submission_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column(
            "help_request_item_id",
            sa.Integer(),
            sa.ForeignKey("help_request_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("units_offered", sa.Integer(), nullable=False),
        sa.Column("donor_name", sa.String(length=160), nullable=False),
        sa.Column("donor_phone", sa.String(length=40), nullable=False),
        sa.Column("pickup_location", sa.String(length=300), nullable=False),
        sa.Column("pickup_latitude", sa.Float()),
        sa.Column("pickup_longitude", sa.Float()),
        sa.Column(
            "pickup_point",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        ),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending_responder"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("contacted_at", sa.DateTime(timezone=True)),
        sa.Column("picked_up_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("units_offered > 0", name="ck_supply_offers_units_positive"),
        sa.CheckConstraint(
            "status IN ('pending_responder', 'responder_assigned', 'contacted', "
            "'picked_up', 'delivered')",
            name="ck_supply_offers_status",
        ),
    )
    op.create_index("ix_supply_offers_status", "supply_offers", ["status"])

    op.create_table(
        "responder_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "supply_offer_id",
            sa.Integer(),
            sa.ForeignKey("supply_offers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("responder_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("supply_offer_id", name="uq_responder_assignments_offer"),
    )


def downgrade() -> None:
    """Remove supply coordination tables in dependency order."""
    op.drop_table("responder_assignments")
    op.drop_index("ix_supply_offers_status", table_name="supply_offers")
    op.drop_table("supply_offers")
    op.drop_index("ix_help_request_items_help_request_id", table_name="help_request_items")
    op.drop_table("help_request_items")
    op.drop_index("idx_help_requests_location", table_name="help_requests")
    op.drop_index("ix_help_requests_status", table_name="help_requests")
    op.drop_table("help_requests")
