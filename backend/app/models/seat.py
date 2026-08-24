from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class SeatCategory(str, Enum):
    PREMIUM = "PREMIUM"
    STANDARD = "STANDARD"


class EventSeatStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"


class VenueSeat(Base):
    __tablename__ = "venue_seats"
    __table_args__ = (
        UniqueConstraint("venue_id", "row_label", "seat_number", name="uq_venue_seat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), nullable=False, index=True)
    row_label: Mapped[str] = mapped_column(String(16), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[SeatCategory] = mapped_column(
        SqlEnum(SeatCategory, native_enum=False),
        nullable=False,
    )
    x_position: Mapped[int] = mapped_column(Integer, nullable=False)
    y_position: Mapped[int] = mapped_column(Integer, nullable=False)

    venue: Mapped["Venue"] = relationship(back_populates="seats")
    event_seats: Mapped[list["EventSeat"]] = relationship(back_populates="venue_seat")


class EventSeat(Base):
    __tablename__ = "event_seats"
    __table_args__ = (
        UniqueConstraint("event_id", "venue_seat_id", name="uq_event_venue_seat"),
        Index("ix_event_seats_event_id", "event_id"),
        Index("ix_event_seats_status", "status"),
        Index("ix_event_seats_hold_expires_at", "hold_expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    venue_seat_id: Mapped[int] = mapped_column(ForeignKey("venue_seats.id"), nullable=False)
    category: Mapped[SeatCategory] = mapped_column(
        SqlEnum(SeatCategory, native_enum=False),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[EventSeatStatus] = mapped_column(
        SqlEnum(EventSeatStatus, native_enum=False),
        nullable=False,
        default=EventSeatStatus.AVAILABLE,
    )
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hold_id: Mapped[str | None] = mapped_column(ForeignKey("seat_holds.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship(back_populates="event_seats")
    venue_seat: Mapped["VenueSeat"] = relationship(back_populates="event_seats")
    hold: Mapped["SeatHold | None"] = relationship(back_populates="event_seats")
    booking_seats: Mapped[list["BookingSeat"]] = relationship(back_populates="event_seat")
    waitlist_offers: Mapped[list["WaitlistOffer"]] = relationship(back_populates="event_seat")

