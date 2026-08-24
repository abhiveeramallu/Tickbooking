from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import utcnow
from app.models.booking import HoldStatus, SeatHold
from app.models.seat import EventSeat, EventSeatStatus, SeatCategory
from app.models.waitlist import Waitlist, WaitlistOffer, WaitlistOfferStatus, WaitlistStatus
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service, booking_service, seat_service, waitlist_service
from app.models.user import UserRole

from .conftest import create_event_with_seats, create_user


def test_register_login_and_invalid_password(db_session):
    result = auth_service.register_user(
        db_session,
        RegisterRequest(name="Rahul", email="rahul@example.com", password="Password123", role=UserRole.CUSTOMER),
    )
    assert result.user.email == "rahul@example.com"
    assert result.access_token

    login_result = auth_service.login_user(
        db_session,
        LoginRequest(email="rahul@example.com", password="Password123"),
    )
    assert login_result.user.id == result.user.id

    with pytest.raises(HTTPException) as exc_info:
        auth_service.login_user(
            db_session,
            LoginRequest(email="rahul@example.com", password="WrongPassword123"),
        )
    assert exc_info.value.status_code == 401


def test_retrieve_seat_map_and_hold_available_seat(db_session):
    bundle = create_event_with_seats(db_session)
    event = bundle["event"]
    seat = bundle["event_seats"][0]
    customer = bundle["customer"]

    seat_map, _ = seat_service.get_event_seat_map(db_session, event.id)
    assert len(seat_map.seats) == 3

    hold, _ = seat_service.hold_seats(db_session, event_id=event.id, seat_ids=[seat.id], user=customer)
    db_session.refresh(seat)
    assert hold.event_id == event.id
    assert seat.status == EventSeatStatus.HELD
    assert seat.hold_id == hold.hold_id


def test_hold_multiple_seats_atomically_and_reject_booked_seat(db_session):
    bundle = create_event_with_seats(db_session)
    customer = bundle["customer"]
    seats = bundle["event_seats"]

    seats[0].status = EventSeatStatus.BOOKED
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
      seat_service.hold_seats(
          db_session,
          event_id=bundle["event"].id,
          seat_ids=[seats[0].id, seats[1].id],
          user=customer,
      )
    assert exc_info.value.status_code == 409
    db_session.refresh(seats[1])
    assert seats[1].status == EventSeatStatus.AVAILABLE


def test_expired_hold_becomes_available(db_session):
    bundle = create_event_with_seats(db_session)
    customer = bundle["customer"]
    seat = bundle["event_seats"][0]

    hold_response, _ = seat_service.hold_seats(db_session, event_id=bundle["event"].id, seat_ids=[seat.id], user=customer)
    hold = db_session.get(SeatHold, hold_response.hold_id)
    hold.expires_at = utcnow() - timedelta(minutes=1)
    seat.hold_expires_at = hold.expires_at
    db_session.commit()

    seat_service.release_expired_holds(db_session)
    db_session.refresh(seat)
    db_session.refresh(hold)
    assert seat.status == EventSeatStatus.AVAILABLE
    assert hold.status == HoldStatus.EXPIRED


def test_booking_valid_hold_wrong_user_and_expired_hold(db_session):
    bundle = create_event_with_seats(db_session)
    event = bundle["event"]
    customer = bundle["customer"]
    wrong_user = bundle["customer_two"]

    first_hold, _ = seat_service.hold_seats(db_session, event_id=event.id, seat_ids=[bundle["event_seats"][0].id], user=customer)
    booking, _, expired = booking_service.create_booking_from_hold(
        db_session,
        hold_id=first_hold.hold_id,
        event_id=event.id,
        user=customer,
    )
    assert booking is not None
    assert expired is False

    second_hold, _ = seat_service.hold_seats(db_session, event_id=event.id, seat_ids=[bundle["event_seats"][1].id], user=customer)
    with pytest.raises(HTTPException) as exc_info:
        booking_service.create_booking_from_hold(
            db_session,
            hold_id=second_hold.hold_id,
            event_id=event.id,
            user=wrong_user,
        )
    assert exc_info.value.status_code == 403

    third_hold, _ = seat_service.hold_seats(db_session, event_id=event.id, seat_ids=[bundle["event_seats"][2].id], user=customer)
    expired_hold = db_session.get(SeatHold, third_hold.hold_id)
    expired_hold.expires_at = utcnow() - timedelta(minutes=1)
    db_session.commit()
    booking, _, expired = booking_service.create_booking_from_hold(
        db_session,
        hold_id=third_hold.hold_id,
        event_id=event.id,
        user=customer,
    )
    assert booking is None
    assert expired is True


def test_waitlist_fifo_cancellation_and_offer_expiry(db_session):
    bundle = create_event_with_seats(db_session)
    event = bundle["event"]
    customer = bundle["customer"]
    customer_two = bundle["customer_two"]
    customer_three = bundle["customer_three"]
    premium_seat = bundle["event_seats"][0]

    hold, _ = seat_service.hold_seats(db_session, event_id=event.id, seat_ids=[premium_seat.id], user=customer)
    booking, _, _ = booking_service.create_booking_from_hold(db_session, hold_id=hold.hold_id, event_id=event.id, user=customer)

    first_wait = waitlist_service.join_waitlist(db_session, event_id=event.id, category=SeatCategory.PREMIUM, user=customer_two)
    second_wait = waitlist_service.join_waitlist(db_session, event_id=event.id, category=SeatCategory.PREMIUM, user=customer_three)
    cancelled_booking, _, offers = booking_service.cancel_booking(db_session, booking_id=booking.id, user=customer)
    assert cancelled_booking.status.value == "CANCELLED"
    assert len(offers) == 1

    first_entry = db_session.get(Waitlist, first_wait.id)
    second_entry = db_session.get(Waitlist, second_wait.id)
    active_offer = db_session.scalar(select(WaitlistOffer).where(WaitlistOffer.waitlist_id == first_wait.id))
    db_session.refresh(premium_seat)
    assert first_entry.status == WaitlistStatus.OFFERED
    assert second_entry.status == WaitlistStatus.WAITING
    assert active_offer.status == WaitlistOfferStatus.PENDING
    assert premium_seat.status == EventSeatStatus.HELD

    active_offer.expires_at = utcnow() - timedelta(minutes=1)
    db_session.commit()
    _, follow_up_offers = waitlist_service.expire_offers(db_session)
    assert len(follow_up_offers) == 1
    db_session.refresh(first_entry)
    db_session.refresh(second_entry)
    assert first_entry.status == WaitlistStatus.REMOVED
    assert second_entry.status == WaitlistStatus.OFFERED


def test_accept_waitlist_offer_becomes_booking(db_session):
    bundle = create_event_with_seats(db_session)
    event = bundle["event"]
    booking_user = bundle["customer"]
    waitlist_user = bundle["customer_two"]
    premium_seat = bundle["event_seats"][0]

    hold, _ = seat_service.hold_seats(db_session, event_id=event.id, seat_ids=[premium_seat.id], user=booking_user)
    booking, _, _ = booking_service.create_booking_from_hold(db_session, hold_id=hold.hold_id, event_id=event.id, user=booking_user)
    waitlist_entry = waitlist_service.join_waitlist(db_session, event_id=event.id, category=SeatCategory.PREMIUM, user=waitlist_user)
    _, _, offers = booking_service.cancel_booking(db_session, booking_id=booking.id, user=booking_user)
    assert offers

    accepted_booking, _, _, expired = waitlist_service.accept_offer(db_session, offer_id=offers[0].id, user=waitlist_user)
    assert accepted_booking is not None
    assert expired is False
    db_session.refresh(premium_seat)
    offer = db_session.get(WaitlistOffer, offers[0].id)
    waitlist_row = db_session.get(Waitlist, waitlist_entry.id)
    assert premium_seat.status == EventSeatStatus.BOOKED
    assert offer.status == WaitlistOfferStatus.ACCEPTED
    assert waitlist_row.status == WaitlistStatus.COMPLETED

