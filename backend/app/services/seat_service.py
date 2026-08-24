from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import ensure_aware, utcnow
from app.models.booking import HoldStatus, SeatHold
from app.models.event import Event, EventStatus
from app.models.seat import EventSeat, EventSeatStatus, VenueSeat
from app.models.user import User
from app.schemas.seat import EventSeatMapResponse, EventSeatResponse, HoldResponse


def get_event_seat_map(db: Session, event_id: int) -> tuple[EventSeatMapResponse, list[dict]]:
    updates = release_expired_holds(db, event_id=event_id)
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    seat_rows = (
        db.execute(
            select(EventSeat)
            .join(EventSeat.venue_seat)
            .options(selectinload(EventSeat.venue_seat))
            .where(EventSeat.event_id == event_id)
            .order_by(VenueSeat.y_position, VenueSeat.x_position, VenueSeat.row_label, VenueSeat.seat_number)
        )
        .scalars()
        .all()
    )
    return EventSeatMapResponse(event_id=event_id, seats=[_to_seat_response(seat) for seat in seat_rows]), updates


def hold_seats(db: Session, *, event_id: int, seat_ids: list[int], user: User) -> tuple[HoldResponse, dict]:
    requested_ids = sorted(set(seat_ids))
    if not requested_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one seat must be selected")

    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status == EventStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event is not available")

    now = utcnow()
    try:
        seats = (
            db.execute(
                select(EventSeat)
                .where(EventSeat.event_id == event_id, EventSeat.id.in_(requested_ids))
                .order_by(EventSeat.id)
                .with_for_update()
            )
            .scalars()
            .all()
        )
        if len(seats) != len(requested_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more seats were not found")

        related_hold_ids = sorted({seat.hold_id for seat in seats if seat.hold_id})
        related_holds = {}
        if related_hold_ids:
            locked_holds = (
                db.execute(
                    select(SeatHold)
                    .where(SeatHold.id.in_(related_hold_ids))
                    .order_by(SeatHold.id)
                    .with_for_update()
                )
                .scalars()
                .all()
            )
            related_holds = {hold.id: hold for hold in locked_holds}

        released_holds: set[str] = set()
        for seat in seats:
            if seat.status == EventSeatStatus.BOOKED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="One or more selected seats are unavailable",
                )
            if seat.status == EventSeatStatus.HELD and seat.hold_id:
                hold = related_holds.get(seat.hold_id)
                if not hold or hold.status != HoldStatus.ACTIVE or ensure_aware(hold.expires_at) <= now:
                    if seat.hold_id not in released_holds and hold:
                        released_holds.add(seat.hold_id)
                        _release_hold_locked(db, hold, HoldStatus.EXPIRED)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="One or more selected seats are unavailable",
                    )
            elif seat.status == EventSeatStatus.HELD:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="One or more selected seats are unavailable",
                )

        for seat in seats:
            if seat.status != EventSeatStatus.AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="One or more selected seats are unavailable",
                )

        hold = SeatHold(
            id=str(uuid4()),
            user_id=user.id,
            event_id=event_id,
            expires_at=now + timedelta(minutes=settings.hold_ttl_minutes),
            status=HoldStatus.ACTIVE,
        )
        db.add(hold)
        db.flush()

        total_amount = Decimal("0.00")
        for seat in seats:
            seat.status = EventSeatStatus.HELD
            seat.hold_id = hold.id
            seat.hold_expires_at = hold.expires_at
            total_amount += Decimal(seat.price)
        db.commit()
    except Exception:
        db.rollback()
        raise

    payload = HoldResponse(
        hold_id=hold.id,
        event_id=event_id,
        seat_ids=requested_ids,
        hold_expires_at=hold.expires_at,
        total_amount=total_amount,
    )
    broadcast = _build_broadcast(
        event_id,
        seats,
        message_type="SEATS_STATUS_CHANGED",
    )
    return payload, broadcast


def release_expired_holds(db: Session, *, event_id: int | None = None) -> list[dict]:
    now = utcnow()
    stmt = select(SeatHold).where(SeatHold.status == HoldStatus.ACTIVE, SeatHold.expires_at <= now)
    if event_id is not None:
        stmt = stmt.where(SeatHold.event_id == event_id)

    updates: dict[int, list[EventSeat]] = defaultdict(list)
    try:
        holds = db.execute(stmt.order_by(SeatHold.expires_at).with_for_update(skip_locked=True)).scalars().all()
        if not holds:
            return []

        for hold in holds:
            if hold.status != HoldStatus.ACTIVE or ensure_aware(hold.expires_at) > now:
                continue
            updates[hold.event_id].extend(_release_hold_locked(db, hold, HoldStatus.EXPIRED))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return [_build_broadcast(event_key, seats, message_type="SEATS_STATUS_CHANGED") for event_key, seats in updates.items() if seats]


def _release_hold_locked(db: Session, hold: SeatHold, terminal_status: HoldStatus) -> list[EventSeat]:
    hold.status = terminal_status
    seats = (
        db.execute(
            select(EventSeat)
            .where(EventSeat.hold_id == hold.id)
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
    return seats


def _to_seat_response(seat: EventSeat) -> EventSeatResponse:
    venue_seat = seat.venue_seat
    return EventSeatResponse(
        id=seat.id,
        row_label=venue_seat.row_label,
        seat_number=venue_seat.seat_number,
        category=seat.category,
        price=seat.price,
        status=seat.status,
        hold_expires_at=seat.hold_expires_at,
        x_position=venue_seat.x_position,
        y_position=venue_seat.y_position,
    )


def _build_broadcast(event_id: int, seats: list[EventSeat], *, message_type: str) -> dict:
    return {
        "type": message_type,
        "event_id": event_id,
        "seats": [
            {
                "seat_id": seat.id,
                "status": seat.status.value,
                "hold_expires_at": seat.hold_expires_at.isoformat() if seat.hold_expires_at else None,
            }
            for seat in sorted(seats, key=lambda item: item.id)
        ],
    }
