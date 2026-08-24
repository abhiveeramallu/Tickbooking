from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.models.seat import SeatCategory


class WaitlistStatus(str, Enum):
    WAITING = "WAITING"
    OFFERED = "OFFERED"
    COMPLETED = "COMPLETED"
    REMOVED = "REMOVED"


class WaitlistOfferStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Waitlist(Base):
    __tablename__ = "waitlist"
    __table_args__ = (
        Index("ix_waitlist_event_id", "event_id"),
        Index("ix_waitlist_category", "category"),
        Index("ix_waitlist_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[SeatCategory] = mapped_column(
        SqlEnum(SeatCategory, native_enum=False),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WaitlistStatus] = mapped_column(
        SqlEnum(WaitlistStatus, native_enum=False),
        nullable=False,
        default=WaitlistStatus.WAITING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship(back_populates="waitlist_entries")
    user: Mapped["User"] = relationship(back_populates="waitlist_entries")
    offers: Mapped[list["WaitlistOffer"]] = relationship(back_populates="waitlist")


class WaitlistOffer(Base):
    __tablename__ = "waitlist_offers"
    __table_args__ = (
        Index("ix_waitlist_offers_expires_at", "expires_at"),
        Index("ix_waitlist_offers_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    waitlist_id: Mapped[int] = mapped_column(ForeignKey("waitlist.id"), nullable=False)
    event_seat_id: Mapped[int] = mapped_column(ForeignKey("event_seats.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[WaitlistOfferStatus] = mapped_column(
        SqlEnum(WaitlistOfferStatus, native_enum=False),
        nullable=False,
        default=WaitlistOfferStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    waitlist: Mapped["Waitlist"] = relationship(back_populates="offers")
    event_seat: Mapped["EventSeat"] = relationship(back_populates="waitlist_offers")

