from datetime import datetime

from pydantic import BaseModel

from app.models.seat import SeatCategory
from app.models.waitlist import WaitlistOfferStatus, WaitlistStatus


class WaitlistCreateRequest(BaseModel):
    category: SeatCategory


class WaitlistResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    category: SeatCategory
    position: int
    status: WaitlistStatus
    created_at: datetime
    event_title: str | None = None


class WaitlistOfferResponse(BaseModel):
    id: int
    waitlist_id: int
    event_seat_id: int
    expires_at: datetime
    status: WaitlistOfferStatus

