"""Create the initial AapdaSetu PostGIS schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-19
"""

from typing import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial tables and spatial indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("region_type", sa.String(length=32), nullable=False),
        sa.Column("district_name", sa.String(length=120), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "boundary",
            geoalchemy2.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_regions_boundary",
        "regions",
        ["boundary"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "shelters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("current_occupancy", sa.Integer(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_shelters_location",
        "shelters",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "sos_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("need_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("urgency", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sos_requests_location",
        "sos_requests",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "volunteer_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("capacity_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_volunteer_offers_location",
        "volunteer_offers",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hazard_type", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column(
            "area",
            geoalchemy2.Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_alerts_area",
        "alerts",
        ["area"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "hazard_risk_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("hazard_type", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "scored_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sos_request_id", sa.Integer(), nullable=False),
        sa.Column("volunteer_offer_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(["sos_request_id"], ["sos_requests.id"]),
        sa.ForeignKeyConstraint(["volunteer_offer_id"], ["volunteer_offers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the application schema but leave the shared PostGIS extension."""
    op.drop_table("matches")
    op.drop_table("hazard_risk_scores")
    op.drop_index("idx_alerts_area", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("idx_volunteer_offers_location", table_name="volunteer_offers")
    op.drop_table("volunteer_offers")
    op.drop_index("idx_sos_requests_location", table_name="sos_requests")
    op.drop_table("sos_requests")
    op.drop_index("idx_shelters_location", table_name="shelters")
    op.drop_table("shelters")
    op.drop_index("idx_regions_boundary", table_name="regions")
    op.drop_table("regions")
