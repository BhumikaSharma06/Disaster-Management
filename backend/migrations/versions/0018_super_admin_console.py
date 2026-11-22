"""Add isolated simulation sessions and privileged-action audit history."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_super_admin_console"
down_revision: str | None = "0017_seed_current_safety_tips"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create simulation and audit tables with a single-running-session guard."""
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_name", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("target_label", sa.String(length=254), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_admin_audit_logs_created_at",
        "admin_audit_logs",
        ["created_at"],
    )
    op.create_table(
        "disaster_simulations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("hazard_type", sa.String(length=64), nullable=False),
        sa.Column("area_name", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("scenario_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column(
            "started_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "stopped_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'stopped')",
            name="ck_disaster_simulations_status",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'moderate', 'high', 'extreme')",
            name="ck_disaster_simulations_severity",
        ),
    )
    op.create_index(
        "uq_disaster_simulations_one_running",
        "disaster_simulations",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
        sqlite_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "ix_disaster_simulations_started_at",
        "disaster_simulations",
        ["started_at"],
    )


def downgrade() -> None:
    """Remove Super Admin console storage."""
    op.drop_index("ix_disaster_simulations_started_at", table_name="disaster_simulations")
    op.drop_index("uq_disaster_simulations_one_running", table_name="disaster_simulations")
    op.drop_table("disaster_simulations")
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
