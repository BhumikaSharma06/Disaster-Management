"""Links between a help request and volunteer capacity."""

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Match(Base):
    """A proposed or confirmed SOS-to-volunteer match."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    sos_request_id: Mapped[int] = mapped_column(ForeignKey("sos_requests.id"), nullable=False)
    volunteer_offer_id: Mapped[int] = mapped_column(
        ForeignKey("volunteer_offers.id"), nullable=False
    )
    distance_km: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
