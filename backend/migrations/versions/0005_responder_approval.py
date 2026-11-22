"""Require administrator approval for responder-role requests.

Revision ID: 0005_responder_approval
Revises: 0004_users_auth
Create Date: 2026-11-22
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_responder_approval"
down_revision: str | None = "0004_users_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add explicit responder request state and revoke unapproved roles."""
    op.add_column(
        "users",
        sa.Column(
            "responder_request_status",
            sa.String(length=16),
            server_default="not_requested",
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE users SET responder_request_status = "
        "CASE WHEN is_responder THEN 'approved' ELSE 'not_requested' END"
    )
    op.create_check_constraint(
        "ck_users_responder_request_status",
        "users",
        "responder_request_status IN ('not_requested', 'pending', 'approved', 'rejected')",
    )
    op.create_check_constraint(
        "ck_users_responder_approval",
        "users",
        "(responder_request_status = 'approved' AND is_responder) OR "
        "(responder_request_status <> 'approved' AND NOT is_responder)",
    )


def downgrade() -> None:
    """Remove responder application state."""
    op.drop_constraint("ck_users_responder_approval", "users", type_="check")
    op.drop_constraint("ck_users_responder_request_status", "users", type_="check")
    op.drop_column("users", "responder_request_status")
