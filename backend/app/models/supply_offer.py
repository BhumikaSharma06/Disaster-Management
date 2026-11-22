"""Quantity-bearing supply offers and responder assignment state."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.help_request import HelpRequestItem
    from app.models.user import User


class SupplyOffer(Base):
    """A donor's offer against one open request item."""

    __tablename__ = "supply_offers"
    __table_args__ = (
        CheckConstraint("units_offered > 0", name="ck_supply_offers_units_positive"),
        CheckConstraint(
            "status IN ('pending_responder', 'responder_assigned', 'contacted', "
            "'picked_up', 'delivered', 'cancelled')",
            name="ck_supply_offers_status",
        ),
        CheckConstraint(
            "actual_units_picked_up IS NULL OR "
            "(actual_units_picked_up >= 0 AND actual_units_picked_up <= units_offered)",
            name="ck_supply_offers_actual_units_picked_up",
        ),
        Index("ix_supply_offers_status", "status"),
        Index("ix_supply_offers_donor_user_id", "donor_user_id"),
        Index(
            "idx_supply_offers_pickup_point",
            "pickup_point",
            postgresql_using="gist",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_submission_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    help_request_item_id: Mapped[int] = mapped_column(
        ForeignKey("help_request_items.id", ondelete="RESTRICT"), nullable=False
    )
    donor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    units_offered: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_units_picked_up: Mapped[int | None] = mapped_column(Integer)
    donor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    donor_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    pickup_location: Mapped[str] = mapped_column(String(300), nullable=False)
    pickup_latitude: Mapped[float | None] = mapped_column()
    pickup_longitude: Mapped[float | None] = mapped_column()
    pickup_point: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending_responder", server_default="pending_responder"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(String(32))
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    help_request_item: Mapped["HelpRequestItem"] = relationship(back_populates="supply_offers")
    assignment: Mapped["ResponderAssignment | None"] = relationship(
        back_populates="supply_offer", uselist=False, cascade="all, delete-orphan"
    )


class ResponderAssignment(Base):
    """The responder who has claimed responsibility for an offer."""

    __tablename__ = "responder_assignments"
    __table_args__ = (UniqueConstraint("supply_offer_id", name="uq_responder_assignments_offer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    supply_offer_id: Mapped[int] = mapped_column(
        ForeignKey("supply_offers.id", ondelete="CASCADE"), nullable=False
    )
    responder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    supply_offer: Mapped[SupplyOffer] = relationship(back_populates="assignment")
    responder: Mapped["User"] = relationship()
