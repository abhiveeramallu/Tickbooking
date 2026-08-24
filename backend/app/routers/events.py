from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.database import get_db
from app.models.booking import Booking, SeatHold
from app.models.event import Event, EventStatus
from app.models.seat import EventSeat, EventSeatStatus, SeatCategory, VenueSeat
from app.models.user import User
from app.models.venue import Venue
from app.models.waitlist import Waitlist, WaitlistOffer
from app.schemas.event import EventCreate, EventListItem, EventListResponse, EventResponse, EventUpdate
from app.services.auth_service import get_current_user, require_organiser


router = APIRouter(prefix="/events", tags=["Events"])


def _serialize_event(event: Event) -> EventResponse:
    return EventResponse.model_validate(event)


@router.get("", response_model=EventListResponse, summary="List events")
async def list_events(
    event_type: str | None = Query(default=None),
    date: str | None = Query(default=None),
    location: str | None = Query(default=None),
    search: str | None = Query(default=None),
    category: SeatCategory | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EventListResponse:
    stmt = select(Event).options(selectinload(Event.venue)).join(Event.venue)
    if category:
        stmt = stmt.join(Event.event_seats).where(EventSeat.category == category)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if date:
        stmt = stmt.where(Event.event_date == date)
    if location:
        stmt = stmt.where(Venue.location.ilike(f"%{location}%"))
    if search:
        stmt = stmt.where(or_(Event.title.ilike(f"%{search}%"), Event.description.ilike(f"%{search}%")))

    events = db.execute(stmt.order_by(Event.event_date, Event.start_time)).scalars().unique().all()
    total = len(events)
    page = events[offset : offset + limit]
    items = [
        EventListItem(
            **EventResponse.model_validate(event).model_dump(),
            starting_price=min(Decimal(event.standard_price), Decimal(event.premium_price)),
        )
        for event in page
    ]
    return EventListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{event_id}", response_model=EventResponse, summary="Get event details")
async def get_event(event_id: int, db: Session = Depends(get_db)) -> EventResponse:
    event = (
        db.execute(select(Event).options(selectinload(Event.venue)).where(Event.id == event_id))
        .scalars()
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return _serialize_event(event)


@router.post("", response_model=EventResponse, status_code=201, summary="Create event")
async def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    organiser: User = Depends(require_organiser),
) -> EventResponse:
    venue = (
        db.execute(select(Venue).options(selectinload(Venue.seats)).where(Venue.id == payload.venue_id))
        .scalars()
        .first()
    )
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    if not venue.seats:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Venue must have seats before creating an event")

    event = Event(organiser_id=organiser.id, **payload.model_dump())
    db.add(event)
    db.flush()

    for venue_seat in sorted(venue.seats, key=lambda seat: seat.id):
        price = event.premium_price if venue_seat.category == SeatCategory.PREMIUM else event.standard_price
        db.add(
            EventSeat(
                event_id=event.id,
                venue_seat_id=venue_seat.id,
                category=venue_seat.category,
                price=price,
                status=EventSeatStatus.AVAILABLE,
            )
        )

    db.commit()
    db.refresh(event)
    event = (
        db.execute(select(Event).options(selectinload(Event.venue)).where(Event.id == event.id))
        .scalars()
        .first()
    )
    return _serialize_event(event)


@router.put("/{event_id}", response_model=EventResponse, summary="Update event")
async def update_event(
    event_id: int,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    organiser: User = Depends(require_organiser),
) -> EventResponse:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.organiser_id != organiser.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    updates = payload.model_dump(exclude_none=True)
    new_venue_id = updates.get("venue_id")
    if new_venue_id and new_venue_id != event.venue_id:
        active_bookings = db.scalar(select(func.count()).select_from(Booking).where(Booking.event_id == event_id))
        busy_seats = db.scalar(
            select(func.count()).select_from(EventSeat).where(
                EventSeat.event_id == event_id,
                EventSeat.status != EventSeatStatus.AVAILABLE,
            )
        )
        if active_bookings or busy_seats:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot change the venue after seat activity has started",
            )

        new_venue = (
            db.execute(select(Venue).options(selectinload(Venue.seats)).where(Venue.id == new_venue_id))
            .scalars()
            .first()
        )
        if not new_venue or not new_venue.seats:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected venue does not have seats")

        db.execute(delete(EventSeat).where(EventSeat.event_id == event_id))
        for venue_seat in sorted(new_venue.seats, key=lambda seat: seat.id):
            price = (
                updates.get("premium_price", event.premium_price)
                if venue_seat.category == SeatCategory.PREMIUM
                else updates.get("standard_price", event.standard_price)
            )
            db.add(
                EventSeat(
                    event_id=event.id,
                    venue_seat_id=venue_seat.id,
                    category=venue_seat.category,
                    price=price,
                    status=EventSeatStatus.AVAILABLE,
                )
            )

    for field, value in updates.items():
        setattr(event, field, value)

    if "premium_price" in updates or "standard_price" in updates:
        seats = db.execute(select(EventSeat).where(EventSeat.event_id == event_id)).scalars().all()
        for seat in seats:
            if seat.status == EventSeatStatus.BOOKED:
                continue
            seat.price = event.premium_price if seat.category == SeatCategory.PREMIUM else event.standard_price

    db.commit()
    db.refresh(event)
    event = (
        db.execute(select(Event).options(selectinload(Event.venue)).where(Event.id == event.id))
        .scalars()
        .first()
    )
    return _serialize_event(event)


@router.delete("/{event_id}", status_code=204, summary="Delete event")
async def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    organiser: User = Depends(require_organiser),
) -> None:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.organiser_id != organiser.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    booking_count = db.scalar(select(func.count()).select_from(Booking).where(Booking.event_id == event_id))
    if booking_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete an event with bookings")

    db.execute(delete(WaitlistOffer).where(WaitlistOffer.event_seat_id.in_(select(EventSeat.id).where(EventSeat.event_id == event_id))))
    db.execute(delete(Waitlist).where(Waitlist.event_id == event_id))
    db.execute(delete(SeatHold).where(SeatHold.event_id == event_id))
    db.execute(delete(EventSeat).where(EventSeat.event_id == event_id))
    db.delete(event)
    db.commit()

