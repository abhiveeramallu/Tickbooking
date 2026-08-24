from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    ORGANISER = "ORGANISER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, native_enum=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_venues: Mapped[list["Venue"]] = relationship(back_populates="creator")
    organised_events: Mapped[list["Event"]] = relationship(back_populates="organiser")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    waitlist_entries: Mapped[list["Waitlist"]] = relationship(back_populates="user")
    seat_holds: Mapped[list["SeatHold"]] = relationship(back_populates="user")

