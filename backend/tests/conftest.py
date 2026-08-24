from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import get_password_hash
from app.database.database import Base
from app.models.event import Event, EventStatus, EventType
from app.models.seat import EventSeat, EventSeatStatus, SeatCategory, VenueSeat
from app.models.user import User, UserRole
from app.models.venue import Venue


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def create_user(db: Session, *, email: str, role: UserRole) -> User:
    user = User(
        name=email.split("@")[0].title(),
        email=email,
        password_hash=get_password_hash("Password123"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_event_with_seats(db: Session) -> dict:
    admin = create_user(db, email="admin@example.com", role=UserRole.ADMIN)
    organiser = create_user(db, email="organiser@example.com", role=UserRole.ORGANISER)
    customer = create_user(db, email="customer@example.com", role=UserRole.CUSTOMER)
    customer_two = create_user(db, email="customer2@example.com", role=UserRole.CUSTOMER)
    customer_three = create_user(db, email="customer3@example.com", role=UserRole.CUSTOMER)

    venue = Venue(name="Central Hall", location="Hyderabad", created_by=admin.id)
    db.add(venue)
    db.flush()

    venue_seats = [
      VenueSeat(venue_id=venue.id, row_label="A", seat_number=1, category=SeatCategory.PREMIUM, x_position=0, y_position=0),
      VenueSeat(venue_id=venue.id, row_label="A", seat_number=2, category=SeatCategory.PREMIUM, x_position=1, y_position=0),
      VenueSeat(venue_id=venue.id, row_label="B", seat_number=1, category=SeatCategory.STANDARD, x_position=0, y_position=1),
    ]
    db.add_all(venue_seats)
    db.flush()

    event = Event(
        organiser_id=organiser.id,
        venue_id=venue.id,
        title="Live Show",
        description="Demo event",
        event_type=EventType.CONCERT,
        event_date=date(2026, 8, 25),
        start_time=time(19, 0),
        end_time=time(21, 0),
        status=EventStatus.PUBLISHED,
        standard_price=Decimal("499.00"),
        premium_price=Decimal("999.00"),
    )
    db.add(event)
    db.flush()

    event_seats = [
        EventSeat(
            event_id=event.id,
            venue_seat_id=seat.id,
            category=seat.category,
            price=Decimal("999.00") if seat.category == SeatCategory.PREMIUM else Decimal("499.00"),
            status=EventSeatStatus.AVAILABLE,
        )
        for seat in venue_seats
    ]
    db.add_all(event_seats)
    db.commit()

    for instance in [venue, event, *event_seats]:
        db.refresh(instance)

    return {
        "admin": admin,
        "organiser": organiser,
        "customer": customer,
        "customer_two": customer_two,
        "customer_three": customer_three,
        "venue": venue,
        "event": event,
        "event_seats": event_seats,
    }

