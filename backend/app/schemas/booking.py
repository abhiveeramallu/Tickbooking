from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus


class BookingCreateRequest(BaseModel):
    hold_id: str = Field(min_length=36, max_length=36)
    event_id: int


class BookingSeatResponse(BaseModel):
    event_seat_id: int
    row_label: str
    seat_number: int
    category: str
    price: Decimal


class BookingEventResponse(BaseModel):
    id: int
    title: str
    event_date: date
    start_time: time
    end_time: time
    venue_name: str
    venue_location: str


class BookingResponse(BaseModel):
    id: int
    booking_reference: str
    event: BookingEventResponse
    seats: list[BookingSeatResponse]
    total_amount: Decimal
    status: BookingStatus
    created_at: datetime
    cancelled_at: datetime | None = None
    qr_code_data_url: str | None = None


class BookingListResponse(BaseModel):
    items: list[BookingResponse]

