"""Active disaster incidents and incident-specific shelter operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Incident(Base):
    """An operator-managed disaster incident and its affected-area label."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'monitoring', 'closed')",
            name="ck_incidents_status",
        ),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    hazard_type: Mapped[str] = mapped_column(String(40), nullable=False)
    area_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class IncidentShelter(Base):
    """A shelter's operator-reported status and occupancy for one incident."""

    __tablename__ = "incident_shelters"
    __table_args__ = (
        UniqueConstraint("incident_id", "shelter_id", name="uq_incident_shelters_incident_shelter"),
        Index("ix_incident_shelters_incident_id", "incident_id"),
        Index("ix_incident_shelters_shelter_id", "shelter_id"),
        CheckConstraint(
            "operational_status IN ('unknown', 'open', 'limited', 'closed')",
            name="ck_incident_shelters_status",
        ),
        CheckConstraint(
            "current_occupancy IS NULL OR current_occupancy >= 0",
            name="ck_incident_shelters_occupancy_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    shelter_id: Mapped[int] = mapped_column(
        ForeignKey("shelters.id", ondelete="CASCADE"), nullable=False
    )
    operational_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown", server_default="unknown"
    )
    current_occupancy: Mapped[int | None] = mapped_column(Integer)
    update_note: Mapped[str | None] = mapped_column(String(500))
    updated_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
