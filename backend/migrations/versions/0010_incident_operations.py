"""Add incident-scoped SOS and operator shelter operations.

Revision ID: 0010_incident_operations
Revises: 0009_coordination_hardening
Create Date: 2026-11-23
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_incident_operations"
down_revision: str | None = "0009_coordination_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create incident lifecycle and incident-scoped operational records."""
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("hazard_type", sa.String(length=40), nullable=False),
        sa.Column("area_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'monitoring', 'closed')",
            name="ck_incidents_status",
        ),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])

    op.create_table(
        "incident_shelters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shelter_id",
            sa.Integer(),
            sa.ForeignKey("shelters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "operational_status",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("current_occupancy", sa.Integer()),
        sa.Column("update_note", sa.String(length=500)),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "incident_id", "shelter_id", name="uq_incident_shelters_incident_shelter"
        ),
        sa.CheckConstraint(
            "operational_status IN ('unknown', 'open', 'limited', 'closed')",
            name="ck_incident_shelters_status",
        ),
        sa.CheckConstraint(
            "current_occupancy IS NULL OR current_occupancy >= 0",
            name="ck_incident_shelters_occupancy_nonnegative",
        ),
    )
    op.create_index("ix_incident_shelters_incident_id", "incident_shelters", ["incident_id"])
    op.create_index("ix_incident_shelters_shelter_id", "incident_shelters", ["shelter_id"])

    op.add_column(
        "sos_requests",
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
        ),
    )
    op.add_column("sos_requests", sa.Column("client_submission_id", sa.Uuid()))
    op.add_column("sos_requests", sa.Column("people_affected", sa.Integer()))
    op.add_column(
        "sos_requests",
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
    )
    op.add_column(
        "sos_requests",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "sos_requests",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sos_requests_incident_id", "sos_requests", ["incident_id"])
    op.create_unique_constraint(
        "uq_sos_requests_client_submission_id", "sos_requests", ["client_submission_id"]
    )
    op.create_check_constraint(
        "ck_sos_requests_people_affected_positive",
        "sos_requests",
        "people_affected IS NULL OR people_affected > 0",
    )
    op.create_check_constraint(
        "ck_sos_requests_status",
        "sos_requests",
        "status IN ('open', 'acknowledged', 'resolved', 'closed')",
    )


def downgrade() -> None:
    """Remove incident operational data and its SOS columns."""
    op.drop_constraint("ck_sos_requests_status", "sos_requests", type_="check")
    op.drop_constraint(
        "ck_sos_requests_people_affected_positive", "sos_requests", type_="check"
    )
    op.drop_constraint(
        "uq_sos_requests_client_submission_id", "sos_requests", type_="unique"
    )
    op.drop_index("ix_sos_requests_incident_id", table_name="sos_requests")
    op.drop_column("sos_requests", "updated_at")
    op.drop_column("sos_requests", "created_at")
    op.drop_column("sos_requests", "updated_by_user_id")
    op.drop_column("sos_requests", "people_affected")
    op.drop_column("sos_requests", "client_submission_id")
    op.drop_column("sos_requests", "incident_id")

    op.drop_index("ix_incident_shelters_shelter_id", table_name="incident_shelters")
    op.drop_index("ix_incident_shelters_incident_id", table_name="incident_shelters")
    op.drop_table("incident_shelters")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_table("incidents")
