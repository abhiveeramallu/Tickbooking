from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.booking import BookingResponse
from app.schemas.waitlist import WaitlistOfferResponse, WaitlistResponse, WaitlistCreateRequest
from app.services import booking_service, waitlist_service
from app.services.auth_service import require_customer
from app.websocket.manager import manager


router = APIRouter(tags=["Waitlist"])


@router.post("/events/{event_id}/waitlist", response_model=WaitlistResponse, status_code=201, summary="Join event waitlist")
async def join_event_waitlist(
    event_id: int,
    payload: WaitlistCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> WaitlistResponse:
    return waitlist_service.join_waitlist(db, event_id=event_id, category=payload.category, user=current_user)


@router.get("/waitlist", response_model=list[WaitlistResponse], summary="List current user waitlist entries")
async def list_waitlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> list[WaitlistResponse]:
    return waitlist_service.list_user_waitlist_entries(db, current_user)


@router.post("/waitlist/offers/{offer_id}/accept", response_model=BookingResponse, summary="Accept a waitlist offer")
async def accept_waitlist_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> BookingResponse:
    booking, broadcast, offers, expired = waitlist_service.accept_offer(db, offer_id=offer_id, user=current_user)
    await manager.broadcast_event(broadcast["event_id"], broadcast)
    waitlist_service.send_offer_emails(db, offers)
    if expired or not booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer expired")

    booking_service.send_booking_email(db, booking.id)
    return booking_service.get_user_booking(db, booking_id=booking.id, user=current_user)

