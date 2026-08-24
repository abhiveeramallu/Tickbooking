from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class EventType(str, Enum):
    MOVIE = "MOVIE"
    CONCERT = "CONCERT"


class EventStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_organiser_id", "organiser_id"),
        Index("ix_events_venue_id", "venue_id"),
        Index("ix_events_event_date", "event_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organiser_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_type: Mapped[EventType] = mapped_column(
        SqlEnum(EventType, native_enum=False),
        nullable=False,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(EventStatus, native_enum=False),
        nullable=False,
        default=EventStatus.PUBLISHED,
    )
    standard_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    premium_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organiser: Mapped["User"] = relationship(back_populates="organised_events")
    venue: Mapped["Venue"] = relationship(back_populates="events")
    event_seats: Mapped[list["EventSeat"]] = relationship(back_populates="event")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="event")
    seat_holds: Mapped[list["SeatHold"]] = relationship(back_populates="event")
    waitlist_entries: Mapped[list["Waitlist"]] = relationship(back_populates="event")

