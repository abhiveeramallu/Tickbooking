from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.seat import EventSeatMapResponse, HoldRequest, HoldResponse
from app.services.auth_service import require_customer
from app.services.seat_service import get_event_seat_map, hold_seats
from app.websocket.manager import manager


router = APIRouter(tags=["Seats"])


@router.get("/events/{event_id}/seats", response_model=EventSeatMapResponse, summary="Get event seat map")
async def get_seat_map(event_id: int, db: Session = Depends(get_db)) -> EventSeatMapResponse:
    seat_map, updates = get_event_seat_map(db, event_id)
    for payload in updates:
        await manager.broadcast_event(payload["event_id"], payload)
    return seat_map


@router.post("/events/{event_id}/holds", response_model=HoldResponse, summary="Hold one or more seats")
async def create_hold(
    event_id: int,
    payload: HoldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> HoldResponse:
    hold_response, broadcast = hold_seats(db, event_id=event_id, seat_ids=payload.seat_ids, user=current_user)
    await manager.broadcast_event(broadcast["event_id"], broadcast)
    return hold_response

