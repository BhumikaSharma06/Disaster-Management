"""Localized alert records; delivery will use a mock gateway."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Alert(Base):
    """An alert message and optional geographic area."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    hazard_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="hi")
    delivery_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    area: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
