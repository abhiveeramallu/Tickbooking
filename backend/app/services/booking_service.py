from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import ensure_aware, utcnow
from app.models.booking import Booking, BookingSeat, BookingStatus, HoldStatus, SeatHold
from app.models.event import Event
from app.models.seat import EventSeat, EventSeatStatus
from app.models.user import User
from app.schemas.booking import BookingEventResponse, BookingResponse, BookingSeatResponse
from app.services import email_service, qr_service


def create_booking_from_hold(db: Session, *, hold_id: str, event_id: int, user: User) -> tuple[Booking | None, dict, bool]:
    booking: Booking | None = None
    expired = False
    broadcast: dict | None = None

    try:
        hold = (
            db.execute(select(SeatHold).where(SeatHold.id == hold_id).with_for_update())
            .scalars()
            .first()
        )
        if not hold or hold.event_id != event_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
        if hold.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This hold belongs to another user")

        seats = (
            db.execute(
                select(EventSeat)
                .where(EventSeat.hold_id == hold.id, EventSeat.event_id == event_id)
                .order_by(EventSeat.id)
                .with_for_update()
            )
            .scalars()
            .all()
        )
        now = utcnow()
        if hold.status != HoldStatus.ACTIVE or ensure_aware(hold.expires_at) <= now:
            hold.status = HoldStatus.EXPIRED
            for seat in seats:
                seat.status = EventSeatStatus.AVAILABLE
                seat.hold_id = None
                seat.hold_expires_at = None
            expired = True
        else:
            for seat in seats:
                if seat.status != EventSeatStatus.HELD or seat.hold_id != hold.id:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hold is no longer valid")
            booking = create_booking_record_locked(db, user=user, event_id=event_id, seats=seats)
            hold.status = HoldStatus.COMPLETED

        broadcast = {
            "type": "SEATS_STATUS_CHANGED",
            "event_id": event_id,
            "seats": [
                {
                    "seat_id": seat.id,
                    "status": seat.status.value,
                    "hold_expires_at": seat.hold_expires_at.isoformat() if seat.hold_expires_at else None,
                }
                for seat in seats
            ],
        }
        db.commit()
    except Exception:
        db.rollback()
        raise

    return booking, broadcast or {}, expired


def create_booking_record_locked(db: Session, *, user: User, event_id: int, seats: list[EventSeat]) -> Booking:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    total_amount = sum((Decimal(seat.price) for seat in seats), Decimal("0.00"))
    booking = Booking(
        booking_reference=_generate_booking_reference(db),
        user_id=user.id,
        event_id=event_id,
        total_amount=total_amount,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    db.flush()

    for seat in seats:
        db.add(
            BookingSeat(
                booking_id=booking.id,
                event_seat_id=seat.id,
                price=seat.price,
            )
        )
        seat.status = EventSeatStatus.BOOKED
        seat.hold_id = None
        seat.hold_expires_at = None

    db.flush()
    return booking


def list_user_bookings(db: Session, user: User) -> list[BookingResponse]:
    bookings = (
        db.execute(
            select(Booking)
            .options(
                selectinload(Booking.event).selectinload(Event.venue),
                selectinload(Booking.booking_seats).selectinload(BookingSeat.event_seat).selectinload(EventSeat.venue_seat),
            )
            .where(Booking.user_id == user.id)
            .order_by(Booking.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [build_booking_response(booking) for booking in bookings]


def get_user_booking(db: Session, *, booking_id: int, user: User) -> BookingResponse:
    booking = (
        db.execute(
            select(Booking)
            .options(
                selectinload(Booking.event).selectinload(Event.venue),
                selectinload(Booking.booking_seats).selectinload(BookingSeat.event_seat).selectinload(EventSeat.venue_seat),
            )
            .where(Booking.id == booking_id, Booking.user_id == user.id)
        )
        .scalars()
        .first()
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return build_booking_response(booking)


def cancel_booking(db: Session, *, booking_id: int, user: User) -> tuple[Booking, dict, list]:
    from app.services import waitlist_service

    follow_up_offers = []
    booking = (
        db.execute(
            select(Booking)
            .options(
                selectinload(Booking.booking_seats).selectinload(BookingSeat.event_seat),
                selectinload(Booking.event).selectinload(Event.venue),
            )
            .where(Booking.id == booking_id, Booking.user_id == user.id)
        )
        .scalars()
        .first()
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    try:
        locked_booking = (
            db.execute(select(Booking).where(Booking.id == booking.id).with_for_update())
            .scalars()
            .first()
        )
        if not locked_booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        if locked_booking.status == BookingStatus.CANCELLED:
            db.refresh(locked_booking)
        else:
            locked_booking.status = BookingStatus.CANCELLED
            locked_booking.cancelled_at = utcnow()
            seat_ids = sorted(booking_seat.event_seat_id for booking_seat in booking.booking_seats)
            seats = (
                db.execute(
                    select(EventSeat)
                    .where(EventSeat.id.in_(seat_ids))
                    .order_by(EventSeat.id)
                    .with_for_update()
                )
                .scalars()
                .all()
            )
            for seat in seats:
                seat.status = EventSeatStatus.AVAILABLE
                seat.hold_id = None
                seat.hold_expires_at = None
                offer = waitlist_service.assign_waitlist_offer_locked(db, seat)
                if offer:
                    follow_up_offers.append(offer)

        broadcast = {
            "type": "SEATS_STATUS_CHANGED",
            "event_id": locked_booking.event_id,
            "seats": [
                {
                    "seat_id": booking_seat.event_seat_id,
                    "status": booking_seat.event_seat.status.value,
                    "hold_expires_at": booking_seat.event_seat.hold_expires_at.isoformat()
                    if booking_seat.event_seat.hold_expires_at
                    else None,
                }
                for booking_seat in booking.booking_seats
            ],
        }
        db.commit()
    except Exception:
        db.rollback()
        raise

    refreshed_booking = (
        db.execute(
            select(Booking)
            .options(
                selectinload(Booking.event).selectinload(Event.venue),
                selectinload(Booking.booking_seats).selectinload(BookingSeat.event_seat).selectinload(EventSeat.venue_seat),
            )
            .where(Booking.id == booking.id)
        )
        .scalars()
        .first()
    )
    return refreshed_booking, broadcast, follow_up_offers


def build_booking_response(booking: Booking) -> BookingResponse:
    event = booking.event
    event_response = BookingEventResponse(
        id=event.id,
        title=event.title,
        event_date=event.event_date,
        start_time=event.start_time,
        end_time=event.end_time,
        venue_name=event.venue.name,
        venue_location=event.venue.location,
    )
    seat_responses = [
        BookingSeatResponse(
            event_seat_id=booking_seat.event_seat_id,
            row_label=booking_seat.event_seat.venue_seat.row_label,
            seat_number=booking_seat.event_seat.venue_seat.seat_number,
            category=booking_seat.event_seat.category.value,
            price=booking_seat.price,
        )
        for booking_seat in sorted(
            booking.booking_seats,
            key=lambda item: (item.event_seat.venue_seat.row_label, item.event_seat.venue_seat.seat_number),
        )
    ]

    qr_code_data_url = None
    if booking.status == BookingStatus.CONFIRMED:
        qr_code_data_url = qr_service.to_data_url(qr_service.generate_qr_code_bytes(booking.booking_reference))

    return BookingResponse(
        id=booking.id,
        booking_reference=booking.booking_reference,
        event=event_response,
        seats=seat_responses,
        total_amount=booking.total_amount,
        status=booking.status,
        created_at=booking.created_at,
        cancelled_at=booking.cancelled_at,
        qr_code_data_url=qr_code_data_url,
    )


def send_booking_email(db: Session, booking_id: int) -> None:
    booking = (
        db.execute(
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.event).selectinload(Event.venue),
                selectinload(Booking.booking_seats).selectinload(BookingSeat.event_seat).selectinload(EventSeat.venue_seat),
            )
            .where(Booking.id == booking_id)
        )
        .scalars()
        .first()
    )
    if not booking:
        return

    qr_bytes = qr_service.generate_qr_code_bytes(booking.booking_reference)
    email_service.send_booking_confirmation_email(
        to_email=booking.user.email,
        booking_reference=booking.booking_reference,
        event_title=booking.event.title,
        venue_name=booking.event.venue.name,
        venue_location=booking.event.venue.location,
        event_datetime=datetime.combine(booking.event.event_date, booking.event.start_time),
        seats=[
            f"{seat.event_seat.venue_seat.row_label}{seat.event_seat.venue_seat.seat_number}"
            for seat in booking.booking_seats
        ],
        total_amount=booking.total_amount,
        qr_code_bytes=qr_bytes,
    )


def _generate_booking_reference(db: Session) -> str:
    for _ in range(10):
        candidate = f"TKT-{secrets.token_hex(3).upper()}"
        exists = db.scalar(select(func.count()).select_from(Booking).where(Booking.booking_reference == candidate))
        if not exists:
            return candidate
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate booking reference")
