"""Volunteer capacity and service locations."""

from geoalchemy2 import Geometry
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VolunteerOffer(Base):
    """A volunteer's available capacity for a type of need."""

    __tablename__ = "volunteer_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    capacity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="available")
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )
