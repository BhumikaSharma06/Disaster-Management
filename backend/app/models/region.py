"""Administrative regions used for risk and response planning."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Region(Base):
    """A district, block, Gram Panchayat, or ward polygon."""

    __tablename__ = "regions"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified', 'verified')",
            name="ck_regions_verification_status",
        ),
        CheckConstraint(
            "length(trim(source_name)) > 0",
            name="ck_regions_source_name_nonempty",
        ),
        CheckConstraint(
            "(verification_status = 'verified' AND verified_at IS NOT NULL "
            "AND verified_by IS NOT NULL AND length(trim(verified_by)) > 0 "
            "AND source_name <> 'Unspecified (legacy record)') OR "
            "(verification_status <> 'verified' AND verified_at IS NULL "
            "AND verified_by IS NULL)",
            name="ck_regions_verification_evidence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region_type: Mapped[str] = mapped_column(String(32), nullable=False)
    district_name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"))
    boundary: Mapped[object] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    source_license: Mapped[str | None] = mapped_column(String(200))
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unverified", server_default="unverified"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(160))
