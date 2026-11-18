"""Victim requests for help and supplies."""

from geoalchemy2 import Geometry
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SOSRequest(Base):
    """A request that can later be matched with a volunteer offer."""

    __tablename__ = "sos_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    need_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )
