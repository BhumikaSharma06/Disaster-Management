"""Emergency shelter locations and capacity."""

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shelter(Base):
    """A mapped shelter and its basic occupancy information."""

    __tablename__ = "shelters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"))
    capacity: Mapped[int | None] = mapped_column(Integer)
    current_occupancy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )
