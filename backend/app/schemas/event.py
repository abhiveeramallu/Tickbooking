from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventStatus, EventType
from app.models.seat import SeatCategory
from app.schemas.venue import VenueResponse


class EventBase(BaseModel):
    venue_id: int
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(default="", max_length=5000)
    event_type: EventType
    event_date: date
    start_time: time
    end_time: time
    status: EventStatus = EventStatus.PUBLISHED
    standard_price: Decimal = Field(gt=0)
    premium_price: Decimal = Field(gt=0)


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    venue_id: int | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    event_type: EventType | None = None
    event_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: EventStatus | None = None
    standard_price: Decimal | None = Field(default=None, gt=0)
    premium_price: Decimal | None = Field(default=None, gt=0)


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organiser_id: int
    created_at: datetime
    venue: VenueResponse


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organiser_id: int
    venue_id: int
    title: str
    description: str
    event_type: EventType
    event_date: date
    start_time: time
    end_time: time
    status: EventStatus
    standard_price: Decimal
    premium_price: Decimal
    created_at: datetime
    venue: VenueResponse
    starting_price: Decimal


class EventListResponse(BaseModel):
    items: list[EventListItem]
    total: int
    limit: int
    offset: int


class EventSummaryMetrics(BaseModel):
    id: int
    title: str
    event_date: date
    start_time: time
    tickets_sold: int
    revenue: Decimal


class OrganiserDashboardResponse(BaseModel):
    total_events: int
    total_bookings: int
    revenue: Decimal
    events: list[EventSummaryMetrics]


class WaitlistJoinPreview(BaseModel):
    category: SeatCategory

