from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.booking import BookingCreateRequest, BookingListResponse, BookingResponse
from app.services import booking_service, waitlist_service
from app.services.auth_service import require_customer
from app.websocket.manager import manager


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, summary="Create booking from a valid hold")
async def create_booking(
    payload: BookingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> BookingResponse:
    booking, broadcast, expired = booking_service.create_booking_from_hold(
        db,
        hold_id=payload.hold_id,
        event_id=payload.event_id,
        user=current_user,
    )
    await manager.broadcast_event(broadcast["event_id"], broadcast)
    if expired or not booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hold expired")

    booking_service.send_booking_email(db, booking.id)
    return booking_service.get_user_booking(db, booking_id=booking.id, user=current_user)


@router.get("", response_model=BookingListResponse, summary="List user bookings")
async def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> BookingListResponse:
    return BookingListResponse(items=booking_service.list_user_bookings(db, current_user))


@router.get("/{booking_id}", response_model=BookingResponse, summary="Get booking details")
async def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> BookingResponse:
    return booking_service.get_user_booking(db, booking_id=booking_id, user=current_user)


@router.post("/{booking_id}/cancel", response_model=BookingResponse, summary="Cancel booking")
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> BookingResponse:
    booking, broadcast, offers = booking_service.cancel_booking(db, booking_id=booking_id, user=current_user)
    await manager.broadcast_event(broadcast["event_id"], broadcast)
    waitlist_service.send_offer_emails(db, offers)
    return booking_service.get_user_booking(db, booking_id=booking.id, user=current_user)

