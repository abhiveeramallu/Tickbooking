import base64
import logging
from datetime import datetime
from decimal import Decimal

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


def send_booking_confirmation_email(
    *,
    to_email: str,
    booking_reference: str,
    event_title: str,
    venue_name: str,
    venue_location: str,
    event_datetime: datetime,
    seats: list[str],
    total_amount: Decimal,
    qr_code_bytes: bytes,
) -> None:
    subject = f"Booking confirmed: {booking_reference}"
    html = f"""
    <h2>Your booking is confirmed</h2>
    <p><strong>Reference:</strong> {booking_reference}</p>
    <p><strong>Event:</strong> {event_title}</p>
    <p><strong>Venue:</strong> {venue_name}, {venue_location}</p>
    <p><strong>Date & Time:</strong> {event_datetime.strftime("%d %b %Y, %I:%M %p")}</p>
    <p><strong>Seats:</strong> {", ".join(seats)}</p>
    <p><strong>Total:</strong> INR {total_amount}</p>
    """
    attachments = [
        {
            "filename": f"{booking_reference}.png",
            "content": base64.b64encode(qr_code_bytes).decode("utf-8"),
            "content_type": "image/png",
        }
    ]
    _send_email(to_email=to_email, subject=subject, html=html, attachments=attachments)


def send_waitlist_offer_email(
    *,
    to_email: str,
    event_title: str,
    seat_label: str,
    category: str,
    expires_at: datetime,
    offer_id: int,
) -> None:
    accept_link = f"{settings.frontend_url.rstrip('/')}/waitlist/offer/{offer_id}"
    subject = f"Seat offer available for {event_title}"
    html = f"""
    <h2>Waitlist offer</h2>
    <p>You have a reserved seat offer for <strong>{event_title}</strong>.</p>
    <p><strong>Seat:</strong> {seat_label}</p>
    <p><strong>Category:</strong> {category}</p>
    <p><strong>Offer expires:</strong> {expires_at.strftime("%d %b %Y, %I:%M %p")}</p>
    <p>Please sign in and accept it here:</p>
    <p><a href="{accept_link}">{accept_link}</a></p>
    """
    _send_email(to_email=to_email, subject=subject, html=html, attachments=[])


def _send_email(*, to_email: str, subject: str, html: str, attachments: list[dict]) -> None:
    provider = settings.email_provider
    if not provider or not settings.email_api_key or not settings.email_from:
        logger.info("Email skipped because provider configuration is missing")
        return

    try:
        if provider == "resend":
            _send_with_resend(to_email=to_email, subject=subject, html=html, attachments=attachments)
        elif provider == "brevo":
            _send_with_brevo(to_email=to_email, subject=subject, html=html, attachments=attachments)
        else:
            logger.warning("Unsupported email provider: %s", provider)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Email delivery failed: %s", exc)


def _send_with_resend(*, to_email: str, subject: str, html: str, attachments: list[dict]) -> None:
    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "attachments": [
            {
                "filename": attachment["filename"],
                "content": attachment["content"],
            }
            for attachment in attachments
        ],
    }
    headers = {"Authorization": f"Bearer {settings.email_api_key}"}
    with httpx.Client(timeout=10) as client:
        response = client.post("https://api.resend.com/emails", json=payload, headers=headers)
        response.raise_for_status()


def _send_with_brevo(*, to_email: str, subject: str, html: str, attachments: list[dict]) -> None:
    payload = {
        "sender": {"email": settings.email_from},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "attachment": [
            {
                "name": attachment["filename"],
                "content": attachment["content"],
            }
            for attachment in attachments
        ],
    }
    headers = {"api-key": settings.email_api_key}
    with httpx.Client(timeout=10) as client:
        response = client.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
        response.raise_for_status()

