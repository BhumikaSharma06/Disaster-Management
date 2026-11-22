"""Store user contact phone and optional saved address."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_user_contact_profile"
down_revision: str | None = "0012_coordination_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add profile fields without requiring changes from existing accounts."""
    op.add_column("users", sa.Column("contact_phone", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("home_state", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("home_district", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("home_locality", sa.String(length=200), nullable=True))
    op.add_column("users", sa.Column("home_landmark", sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Remove saved contact and address fields."""
    op.drop_column("users", "home_landmark")
    op.drop_column("users", "home_locality")
    op.drop_column("users", "home_district")
    op.drop_column("users", "home_state")
    op.drop_column("users", "contact_phone")
