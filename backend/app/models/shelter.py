"""Emergency shelter locations and capacity."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shelter(Base):
    """A mapped shelter and its basic occupancy information."""

    __tablename__ = "shelters"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified', 'verified')",
            name="ck_shelters_verification_status",
        ),
        CheckConstraint(
            "length(trim(source_name)) > 0",
            name="ck_shelters_source_name_nonempty",
        ),
        CheckConstraint(
            "(verification_status = 'verified' AND verified_at IS NOT NULL "
            "AND verified_by IS NOT NULL AND length(trim(verified_by)) > 0 "
            "AND source_name <> 'Unspecified (legacy record)') OR "
            "(verification_status <> 'verified' AND verified_at IS NULL "
            "AND verified_by IS NULL)",
            name="ck_shelters_verification_evidence",
        ),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_shelters_capacity_positive"),
        CheckConstraint("current_occupancy >= 0", name="ck_shelters_occupancy_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"))
    capacity: Mapped[int | None] = mapped_column(Integer)
    current_occupancy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    source_license: Mapped[str | None] = mapped_column(String(200))
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unverified", server_default="unverified"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(160))
