
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TripRequirement(Base):
    """旅行需求模型"""

    __tablename__ = "trip_requirements"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )

    departure_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    travelers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    travel_style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="sightseeing",
    )

    travel_pace: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="moderate",
    )

    transport_preference: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="public_transport",
    )

    accommodation_preference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    daily_start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(9, 0),
    )

    daily_end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(20, 0),
    )

    must_visit_places: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    excluded_places: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    preferred_activities: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    special_requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            name="uq_trip_requirements_trip_id",
        ),
    )
