
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class TripItinerary(Base):
    """AI 旅行规划结果，支持同一旅行保存多个版本。"""

    __tablename__ = "trip_itineraries"

    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "version",
            name="uq_trip_itinerary_version",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
    )

    itinerary: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    route_data: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    quality_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    validation_passed: Mapped[bool | None] = mapped_column(
        nullable=True,
    )

    quality_passed: Mapped[bool | None] = mapped_column(
        nullable=True,
    )

    route_validation_passed: Mapped[bool | None] = mapped_column(
        nullable=True,
    )

    route_warnings: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    route_adjustments: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now,
    )
