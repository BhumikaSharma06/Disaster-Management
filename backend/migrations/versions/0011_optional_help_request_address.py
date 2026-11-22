"""Make administrative address details optional for coordinate-based requests.

Revision ID: 0011_optional_help_request_address
Revises: 0010_incident_operations
Create Date: 2026-11-22
"""

from typing import Sequence

from alembic import op

revision: str = "0011_optional_address"
down_revision: str | None = "0010_incident_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow coordinate-only help requests when reverse geocoding is unavailable."""
    for column in ("state", "district", "locality"):
        op.alter_column("help_requests", column, nullable=True)


def downgrade() -> None:
    """Restore required address fields with empty values for coordinate-only rows."""
    op.execute(
        "UPDATE help_requests SET state = COALESCE(state, ''), "
        "district = COALESCE(district, ''), locality = COALESCE(locality, '')"
    )
    for column in ("state", "district", "locality"):
        op.alter_column("help_requests", column, nullable=False)
