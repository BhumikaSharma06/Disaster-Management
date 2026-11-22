"""Add source provenance and verification state to geographic records.

Revision ID: 0002_geography_provenance
Revises: 0001_initial_schema
Create Date: 2026-11-19
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_geography_provenance"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_SOURCE = "Unspecified (legacy record)"


def _add_provenance_columns(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column(
            "source_name",
            sa.String(length=200),
            server_default=LEGACY_SOURCE,
            nullable=False,
        ),
    )
    op.alter_column(table_name, "source_name", server_default=None)
    op.add_column(
        table_name,
        sa.Column("source_reference", sa.String(length=500), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column("source_license", sa.String(length=200), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column(
            "verification_status",
            sa.String(length=16),
            server_default="unverified",
            nullable=False,
        ),
    )
    op.add_column(
        table_name,
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column("verified_by", sa.String(length=160), nullable=True),
    )
    op.create_check_constraint(
        f"ck_{table_name}_verification_status",
        table_name,
        "verification_status IN ('unverified', 'verified')",
    )
    op.create_check_constraint(
        f"ck_{table_name}_source_name_nonempty",
        table_name,
        "length(trim(source_name)) > 0",
    )
    op.create_check_constraint(
        f"ck_{table_name}_verification_evidence",
        table_name,
        "(verification_status = 'verified' AND verified_at IS NOT NULL "
        "AND verified_by IS NOT NULL AND length(trim(verified_by)) > 0 "
        f"AND source_name <> '{LEGACY_SOURCE}') OR "
        "(verification_status <> 'verified' AND verified_at IS NULL "
        "AND verified_by IS NULL)",
    )


def upgrade() -> None:
    """Add provenance columns while retaining existing rows as unverified."""
    _add_provenance_columns("regions")
    _add_provenance_columns("shelters")
    op.create_check_constraint(
        "ck_shelters_capacity_positive",
        "shelters",
        "capacity IS NULL OR capacity > 0",
    )
    op.create_check_constraint(
        "ck_shelters_occupancy_nonnegative",
        "shelters",
        "current_occupancy >= 0",
    )


def downgrade() -> None:
    """Remove verification metadata and its constraints."""
    op.drop_constraint("ck_shelters_occupancy_nonnegative", "shelters", type_="check")
    op.drop_constraint("ck_shelters_capacity_positive", "shelters", type_="check")
    for table_name in ("shelters", "regions"):
        op.drop_constraint(
            f"ck_{table_name}_verification_evidence", table_name, type_="check"
        )
        op.drop_constraint(
            f"ck_{table_name}_source_name_nonempty", table_name, type_="check"
        )
        op.drop_constraint(
            f"ck_{table_name}_verification_status", table_name, type_="check"
        )
        op.drop_column(table_name, "verified_by")
        op.drop_column(table_name, "verified_at")
        op.drop_column(table_name, "verification_status")
        op.drop_column(table_name, "source_license")
        op.drop_column(table_name, "source_reference")
        op.drop_column(table_name, "source_name")
