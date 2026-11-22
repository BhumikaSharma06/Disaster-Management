"""Admin-authored hazard safety guidance."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SafetyTip(Base):
    """A published or draft piece of hazard-specific safety guidance."""

    __tablename__ = "safety_tips"
    __table_args__ = (
        CheckConstraint(
            "phase IN ('before', 'during', 'after')",
            name="ck_safety_tips_phase",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_safety_tips_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    hazard_type: Mapped[str] = mapped_column(String(64), nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    region: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    source: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
