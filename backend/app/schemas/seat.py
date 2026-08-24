from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.seat import EventSeatStatus, SeatCategory


class EventSeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_label: str
    seat_number: int
    category: SeatCategory
    price: Decimal
    status: EventSeatStatus
    hold_expires_at: datetime | None = None
    x_position: int
    y_position: int


class EventSeatMapResponse(BaseModel):
    event_id: int
    seats: list[EventSeatResponse]


class HoldRequest(BaseModel):
    seat_ids: list[int] = Field(min_length=1)


class HoldResponse(BaseModel):
    hold_id: str
    event_id: int
    seat_ids: list[int]
    hold_expires_at: datetime
    total_amount: Decimal


class SeatBroadcastItem(BaseModel):
    seat_id: int
    status: EventSeatStatus
    hold_expires_at: datetime | None = None


class SeatBroadcastMessage(BaseModel):
    type: str
    event_id: int
    seats: list[SeatBroadcastItem]

