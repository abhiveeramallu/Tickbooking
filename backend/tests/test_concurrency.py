import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import get_password_hash
from app.database.database import Base
from app.models.event import Event, EventStatus, EventType
from app.models.seat import EventSeat, EventSeatStatus, SeatCategory, VenueSeat
from app.models.user import User, UserRole
from app.models.venue import Venue
from app.services import booking_service, seat_service, waitlist_service


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL or "postgresql" not in TEST_DATABASE_URL,
    reason="PostgreSQL TEST_DATABASE_URL is required for row-locking concurrency tests",
)


def _build_postgres_fixture(session: Session) -> dict:
    admin = User(name="Admin", email="admin+pg@example.com", password_hash=get_password_hash("Password123"), role=UserRole.ADMIN)
    organiser = User(name="Organiser", email="organiser+pg@example.com", password_hash=get_password_hash("Password123"), role=UserRole.ORGANISER)
    user_one = User(name="One", email="one+pg@example.com", password_hash=get_password_hash("Password123"), role=UserRole.CUSTOMER)
    user_two = User(name="Two", email="two+pg@example.com", password_hash=get_password_hash("Password123"), role=UserRole.CUSTOMER)
    user_three = User(name="Three", email="three+pg@example.com", password_hash=get_password_hash("Password123"), role=UserRole.CUSTOMER)
    session.add_all([admin, organiser, user_one, user_two, user_three])
    session.flush()

    venue = Venue(name="PG Hall", location="Bengaluru", created_by=admin.id)
    session.add(venue)
    session.flush()

    venue_seat = VenueSeat(
        venue_id=venue.id,
        row_label="A",
        seat_number=1,
        category=SeatCategory.PREMIUM,
        x_position=0,
        y_position=0,
    )
    session.add(venue_seat)
    session.flush()

    event = Event(
        organiser_id=organiser.id,
        venue_id=venue.id,
        title="Concurrency Event",
        description="Postgres lock test",
        event_type=EventType.CONCERT,
        event_date=date(2026, 8, 25),
        start_time=time(20, 0),
        end_time=time(22, 0),
        status=EventStatus.PUBLISHED,
        standard_price=Decimal("400.00"),
        premium_price=Decimal("800.00"),
    )
    session.add(event)
    session.flush()

    event_seat = EventSeat(
        event_id=event.id,
        venue_seat_id=venue_seat.id,
        category=SeatCategory.PREMIUM,
        price=Decimal("800.00"),
        status=EventSeatStatus.AVAILABLE,
    )
    session.add(event_seat)
    session.commit()

    return {
        "event_id": event.id,
        "seat_id": event_seat.id,
        "user_one_id": user_one.id,
        "user_two_id": user_two.id,
        "user_three_id": user_three.id,
    }


@pytest.fixture()
def postgres_session_factory():
    engine = create_engine(TEST_DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_only_one_user_can_hold_the_same_seat(postgres_session_factory):
    session = postgres_session_factory()
    fixture = _build_postgres_fixture(session)
    session.close()

    def attempt_hold(user_id: int) -> bool:
        worker_session = postgres_session_factory()
        user = worker_session.get(User, user_id)
        try:
            seat_service.hold_seats(
                worker_session,
                event_id=fixture["event_id"],
                seat_ids=[fixture["seat_id"]],
                user=user,
            )
            return True
        except HTTPException as exc:
            assert exc.status_code == 409
            return False
        finally:
            worker_session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_hold, [fixture["user_one_id"], fixture["user_two_id"]]))

    assert sum(results) == 1


def test_only_one_acceptance_can_book_a_waitlist_offer(postgres_session_factory):
    session = postgres_session_factory()
    fixture = _build_postgres_fixture(session)
    user_one = session.get(User, fixture["user_one_id"])
    user_two = session.get(User, fixture["user_two_id"])
    user_three = session.get(User, fixture["user_three_id"])

    hold, _ = seat_service.hold_seats(session, event_id=fixture["event_id"], seat_ids=[fixture["seat_id"]], user=user_one)
    booking, _, _ = booking_service.create_booking_from_hold(session, hold_id=hold.hold_id, event_id=fixture["event_id"], user=user_one)
    waitlist_service.join_waitlist(session, event_id=fixture["event_id"], category=SeatCategory.PREMIUM, user=user_two)
    _, _, offers = booking_service.cancel_booking(session, booking_id=booking.id, user=user_one)
    offer_id = offers[0].id
    session.close()

    def attempt_accept(user_id: int):
        worker_session = postgres_session_factory()
        user = worker_session.get(User, user_id)
        try:
            booking, _, _, _ = waitlist_service.accept_offer(worker_session, offer_id=offer_id, user=user)
            return booking is not None
        except HTTPException:
            return False
        finally:
            worker_session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_accept, [fixture["user_two_id"], fixture["user_three_id"]]))

    assert sum(results) == 1
