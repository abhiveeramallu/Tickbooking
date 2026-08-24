from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import ensure_aware, utcnow
from app.models.booking import Booking, BookingSeat
from app.models.event import Event
from app.models.seat import EventSeat, EventSeatStatus, SeatCategory
from app.models.user import User
from app.models.waitlist import Waitlist, WaitlistOffer, WaitlistOfferStatus, WaitlistStatus
from app.schemas.waitlist import WaitlistOfferResponse, WaitlistResponse
from app.services import email_service


def join_waitlist(db: Session, *, event_id: int, category: SeatCategory, user: User) -> WaitlistResponse:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    existing = db.scalar(
        select(Waitlist).where(
            Waitlist.event_id == event_id,
            Waitlist.user_id == user.id,
            Waitlist.category == category,
            Waitlist.status.in_([WaitlistStatus.WAITING, WaitlistStatus.OFFERED]),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already on the waitlist for this category")

    next_position = (
        db.scalar(
            select(func.coalesce(func.max(Waitlist.position), 0) + 1).where(
                Waitlist.event_id == event_id,
                Waitlist.category == category,
            )
        )
        or 1
    )
    entry = Waitlist(
        event_id=event_id,
        user_id=user.id,
        category=category,
        position=next_position,
        status=WaitlistStatus.WAITING,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return WaitlistResponse(
        id=entry.id,
        event_id=entry.event_id,
        user_id=entry.user_id,
        category=entry.category,
        position=entry.position,
        status=entry.status,
        created_at=entry.created_at,
        event_title=event.title,
    )


def list_user_waitlist_entries(db: Session, user: User) -> list[WaitlistResponse]:
    entries = (
        db.execute(
            select(Waitlist)
            .options(selectinload(Waitlist.event))
            .where(Waitlist.user_id == user.id)
            .order_by(Waitlist.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        WaitlistResponse(
            id=entry.id,
            event_id=entry.event_id,
            user_id=entry.user_id,
            category=entry.category,
            position=entry.position,
            status=entry.status,
            created_at=entry.created_at,
            event_title=entry.event.title if entry.event else None,
        )
        for entry in entries
    ]


def assign_waitlist_offer_locked(db: Session, seat: EventSeat) -> WaitlistOffer | None:
    queue_entry = (
        db.execute(
            select(Waitlist)
            .where(
                Waitlist.event_id == seat.event_id,
                Waitlist.category == seat.category,
                Waitlist.status == WaitlistStatus.WAITING,
            )
            .order_by(Waitlist.position, Waitlist.created_at, Waitlist.id)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .first()
    )
    if not queue_entry:
        seat.status = EventSeatStatus.AVAILABLE
        seat.hold_id = None
        seat.hold_expires_at = None
        return None

    queue_entry.status = WaitlistStatus.OFFERED
    offer = WaitlistOffer(
        waitlist_id=queue_entry.id,
        event_seat_id=seat.id,
        expires_at=utcnow() + timedelta(minutes=settings.waitlist_offer_ttl_minutes),
        status=WaitlistOfferStatus.PENDING,
    )
    db.add(offer)
    db.flush()

    seat.status = EventSeatStatus.HELD
    seat.hold_id = None
    seat.hold_expires_at = None
    return offer


def accept_offer(db: Session, *, offer_id: int, user: User) -> tuple[Booking | None, dict, list[WaitlistOffer], bool]:
    from app.services import booking_service

    follow_up_offers: list[WaitlistOffer] = []
    booking: Booking | None = None
    expired = False
    seat_broadcast: dict | None = None

    try:
        offer = (
            db.execute(select(WaitlistOffer).where(WaitlistOffer.id == offer_id).with_for_update())
            .scalars()
            .first()
        )
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

        waitlist_entry = (
            db.execute(select(Waitlist).where(Waitlist.id == offer.waitlist_id).with_for_update())
            .scalars()
            .first()
        )
        if not waitlist_entry or waitlist_entry.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this offer")

        seat = (
            db.execute(select(EventSeat).where(EventSeat.id == offer.event_seat_id).with_for_update())
            .scalars()
            .first()
        )
        if not seat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")

        now = utcnow()
        if offer.status != WaitlistOfferStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer is no longer available")

        if ensure_aware(offer.expires_at) <= now:
            offer.status = WaitlistOfferStatus.EXPIRED
            waitlist_entry.status = WaitlistStatus.REMOVED
            next_offer = assign_waitlist_offer_locked(db, seat)
            if next_offer:
                follow_up_offers.append(next_offer)
            expired = True
        else:
            if seat.status != EventSeatStatus.HELD or seat.id != offer.event_seat_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer seat is unavailable")

            booking = booking_service.create_booking_record_locked(
                db,
                user=user,
                event_id=waitlist_entry.event_id,
                seats=[seat],
            )
            offer.status = WaitlistOfferStatus.ACCEPTED
            waitlist_entry.status = WaitlistStatus.COMPLETED

        seat_broadcast = {
            "type": "SEATS_STATUS_CHANGED",
            "event_id": seat.event_id,
            "seats": [
                {
                    "seat_id": seat.id,
                    "status": seat.status.value,
                    "hold_expires_at": seat.hold_expires_at.isoformat() if seat.hold_expires_at else None,
                }
            ],
        }
        db.commit()
    except Exception:
        db.rollback()
        raise

    return booking, seat_broadcast or {}, follow_up_offers, expired


def expire_offers(db: Session) -> tuple[list[dict], list[WaitlistOffer]]:
    now = utcnow()
    broadcasts: dict[int, list[dict]] = defaultdict(list)
    follow_up_offers: list[WaitlistOffer] = []

    try:
        expired_offers = (
            db.execute(
                select(WaitlistOffer)
                .where(
                    WaitlistOffer.status == WaitlistOfferStatus.PENDING,
                    WaitlistOffer.expires_at <= now,
                )
                .order_by(WaitlistOffer.expires_at, WaitlistOffer.id)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )
        if not expired_offers:
            return [], []

        for offer in expired_offers:
            if offer.status != WaitlistOfferStatus.PENDING or ensure_aware(offer.expires_at) > now:
                continue

            waitlist_entry = (
                db.execute(select(Waitlist).where(Waitlist.id == offer.waitlist_id).with_for_update())
                .scalars()
                .first()
            )
            seat = (
                db.execute(select(EventSeat).where(EventSeat.id == offer.event_seat_id).with_for_update())
                .scalars()
                .first()
            )
            if not waitlist_entry or not seat:
                continue

            offer.status = WaitlistOfferStatus.EXPIRED
            waitlist_entry.status = WaitlistStatus.REMOVED
            next_offer = assign_waitlist_offer_locked(db, seat)
            if next_offer:
                follow_up_offers.append(next_offer)

            broadcasts[seat.event_id].append(
                {
                    "seat_id": seat.id,
                    "status": seat.status.value,
                    "hold_expires_at": seat.hold_expires_at.isoformat() if seat.hold_expires_at else None,
                }
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return [
        {"type": "SEATS_STATUS_CHANGED", "event_id": event_id, "seats": seats}
        for event_id, seats in broadcasts.items()
    ], follow_up_offers


def send_offer_emails(db: Session, offers: list[WaitlistOffer]) -> None:
    if not offers:
        return

    hydrated_offers = (
        db.execute(
            select(WaitlistOffer)
            .options(
                selectinload(WaitlistOffer.waitlist).selectinload(Waitlist.user),
                selectinload(WaitlistOffer.waitlist).selectinload(Waitlist.event),
                selectinload(WaitlistOffer.event_seat).selectinload(EventSeat.venue_seat),
            )
            .where(WaitlistOffer.id.in_([offer.id for offer in offers]))
        )
        .scalars()
        .all()
    )

    for offer in hydrated_offers:
        waitlist_entry = offer.waitlist
        user = waitlist_entry.user
        event = waitlist_entry.event
        seat = offer.event_seat
        email_service.send_waitlist_offer_email(
            to_email=user.email,
            event_title=event.title,
            seat_label=f"{seat.venue_seat.row_label}{seat.venue_seat.seat_number}",
            category=seat.category.value,
            expires_at=offer.expires_at,
            offer_id=offer.id,
        )
