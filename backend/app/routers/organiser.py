from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.database import get_db
from app.models.booking import BookingStatus
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventSummaryMetrics, OrganiserDashboardResponse
from app.services.auth_service import require_organiser


router = APIRouter(prefix="/organiser", tags=["Organiser"])


@router.get("/dashboard", response_model=OrganiserDashboardResponse, summary="Get organiser dashboard metrics")
async def organiser_dashboard(
    db: Session = Depends(get_db),
    organiser: User = Depends(require_organiser),
) -> OrganiserDashboardResponse:
    events = (
        db.execute(
            select(Event)
            .options(selectinload(Event.bookings))
            .where(Event.organiser_id == organiser.id)
            .order_by(Event.event_date, Event.start_time)
        )
        .scalars()
        .all()
    )

    metrics = []
    total_bookings = 0
    revenue = Decimal("0.00")
    for event in events:
        confirmed = [booking for booking in event.bookings if booking.status == BookingStatus.CONFIRMED]
        sold = len(confirmed)
        event_revenue = sum((Decimal(booking.total_amount) for booking in confirmed), Decimal("0.00"))
        total_bookings += sold
        revenue += event_revenue
        metrics.append(
            EventSummaryMetrics(
                id=event.id,
                title=event.title,
                event_date=event.event_date,
                start_time=event.start_time,
                tickets_sold=sold,
                revenue=event_revenue,
            )
        )

    return OrganiserDashboardResponse(
        total_events=len(events),
        total_bookings=total_bookings,
        revenue=revenue,
        events=metrics,
    )

