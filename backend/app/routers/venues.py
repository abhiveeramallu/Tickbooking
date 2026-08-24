from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.database.database import get_db
from app.models.event import Event
from app.models.seat import EventSeat, VenueSeat
from app.models.user import User
from app.models.venue import Venue
from app.schemas.venue import VenueCreate, VenueResponse, VenueSeatCreate, VenueSeatResponse, VenueSeatUpdate, VenueUpdate
from app.services.auth_service import require_admin


router = APIRouter(prefix="/venues", tags=["Venues"])


@router.get("", response_model=list[VenueResponse], summary="List venues")
async def list_venues(
    include_seats: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[VenueResponse]:
    stmt = select(Venue)
    if include_seats:
        stmt = stmt.options(selectinload(Venue.seats))
    venues = db.execute(stmt.order_by(Venue.created_at.desc())).scalars().unique().all()
    return [VenueResponse.model_validate(venue) for venue in venues]


@router.get("/{venue_id}", response_model=VenueResponse, summary="Get venue details")
async def get_venue(venue_id: int, db: Session = Depends(get_db)) -> VenueResponse:
    venue = (
        db.execute(select(Venue).options(selectinload(Venue.seats)).where(Venue.id == venue_id))
        .scalars()
        .first()
    )
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    return VenueResponse.model_validate(venue)


@router.post("", response_model=VenueResponse, status_code=201, summary="Create venue")
async def create_venue(
    payload: VenueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> VenueResponse:
    venue = Venue(name=payload.name.strip(), location=payload.location.strip(), created_by=current_user.id)
    db.add(venue)
    db.flush()
    for seat_payload in payload.seats:
        db.add(
            VenueSeat(
                venue_id=venue.id,
                row_label=seat_payload.row_label.strip().upper(),
                seat_number=seat_payload.seat_number,
                category=seat_payload.category,
                x_position=seat_payload.x_position,
                y_position=seat_payload.y_position,
            )
        )
    db.commit()
    db.refresh(venue)
    venue = (
        db.execute(select(Venue).options(selectinload(Venue.seats)).where(Venue.id == venue.id))
        .scalars()
        .first()
    )
    return VenueResponse.model_validate(venue)


@router.put("/{venue_id}", response_model=VenueResponse, summary="Update venue")
async def update_venue(
    venue_id: int,
    payload: VenueUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> VenueResponse:
    venue = db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(venue, field, value.strip() if isinstance(value, str) else value)

    db.commit()
    db.refresh(venue)
    venue = (
        db.execute(select(Venue).options(selectinload(Venue.seats)).where(Venue.id == venue.id))
        .scalars()
        .first()
    )
    return VenueResponse.model_validate(venue)


@router.delete("/{venue_id}", status_code=204, summary="Delete venue")
async def delete_venue(
    venue_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    venue = db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    has_events = db.scalar(select(func.count()).select_from(Event).where(Event.venue_id == venue_id))
    if has_events:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Delete events before removing the venue")
    db.execute(delete(VenueSeat).where(VenueSeat.venue_id == venue_id))
    db.delete(venue)
    db.commit()


@router.post("/{venue_id}/seats", response_model=VenueSeatResponse, status_code=201, summary="Add seat to venue")
async def create_venue_seat(
    venue_id: int,
    payload: VenueSeatCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> VenueSeatResponse:
    venue = db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    seat = VenueSeat(
        venue_id=venue_id,
        row_label=payload.row_label.strip().upper(),
        seat_number=payload.seat_number,
        category=payload.category,
        x_position=payload.x_position,
        y_position=payload.y_position,
    )
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return VenueSeatResponse.model_validate(seat)


@router.put("/{venue_id}/seats/{seat_id}", response_model=VenueSeatResponse, summary="Update venue seat")
async def update_venue_seat(
    venue_id: int,
    seat_id: int,
    payload: VenueSeatUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> VenueSeatResponse:
    seat = db.get(VenueSeat, seat_id)
    if not seat or seat.venue_id != venue_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(seat, field, value.strip().upper() if field == "row_label" else value)
    db.commit()
    db.refresh(seat)
    return VenueSeatResponse.model_validate(seat)


@router.delete("/{venue_id}/seats/{seat_id}", status_code=204, summary="Delete venue seat")
async def delete_venue_seat(
    venue_id: int,
    seat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    seat = db.get(VenueSeat, seat_id)
    if not seat or seat.venue_id != venue_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    linked_event_seats = db.scalar(select(func.count()).select_from(EventSeat).where(EventSeat.venue_seat_id == seat_id))
    if linked_event_seats:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat is already used by an event")
    db.delete(seat)
    db.commit()

