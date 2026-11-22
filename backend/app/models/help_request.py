"""Community requests for specific help items."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.supply_offer import SupplyOffer


class HelpRequest(Base):
    """A geolocated request submitted by a community member."""

    __tablename__ = "help_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'partially_fulfilled', 'fulfilled', 'closed', 'cancelled')",
            name="ck_help_requests_status",
        ),
        CheckConstraint(
            "moderation_reason IS NULL OR moderation_reason IN ('spam', 'duplicate')",
            name="ck_help_requests_moderation_reason",
        ),
        Index("idx_help_requests_location", "location", postgresql_using="gist"),
        Index("ix_help_requests_created_by_user_id", "created_by_user_id"),
        Index("ix_help_requests_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_submission_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    urgency: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    locality: Mapped[str | None] = mapped_column(String(200))
    landmark: Mapped[str | None] = mapped_column(String(200))
    contact_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    moderation_reason: Mapped[str | None] = mapped_column(String(16))
    moderated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    items: Mapped[list["HelpRequestItem"]] = relationship(
        back_populates="help_request", cascade="all, delete-orphan", order_by="HelpRequestItem.id"
    )


class HelpRequestItem(Base):
    """A quantity-tracked item required by a help request."""

    __tablename__ = "help_request_items"
    __table_args__ = (
        CheckConstraint("units_required > 0", name="ck_help_request_items_required_positive"),
        CheckConstraint("units_fulfilled >= 0", name="ck_help_request_items_fulfilled_nonnegative"),
        CheckConstraint(
            "units_fulfilled <= units_required", name="ck_help_request_items_fulfilled_limit"
        ),
        Index("ix_help_request_items_help_request_id", "help_request_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    help_request_id: Mapped[int] = mapped_column(
        ForeignKey("help_requests.id", ondelete="CASCADE"), nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    units_required: Mapped[int] = mapped_column(Integer, nullable=False)
    units_fulfilled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_label: Mapped[str] = mapped_column(String(40), nullable=False, default="units")
    help_request: Mapped[HelpRequest] = relationship(back_populates="items")
    supply_offers: Mapped[list["SupplyOffer"]] = relationship(back_populates="help_request_item")
