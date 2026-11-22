"""Shared token-bucket state for public coordination submissions."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoordinationRateLimit(Base):
    """One cross-process submission-rate bucket per endpoint and client address."""

    __tablename__ = "coordination_rate_limits"
    __table_args__ = (Index("ix_coordination_rate_limits_updated_at", "updated_at"),)

    bucket_key: Mapped[str] = mapped_column(String(300), primary_key=True)
    available_tokens: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
