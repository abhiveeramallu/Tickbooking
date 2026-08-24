import asyncio
import logging

from app.database.database import SessionLocal
from app.services import waitlist_service
from app.websocket.manager import manager


logger = logging.getLogger(__name__)


def run_waitlist_expiry_job() -> None:
    db = SessionLocal()
    try:
        broadcasts, offers = waitlist_service.expire_offers(db)
        for payload in broadcasts:
            asyncio.run(manager.broadcast_event(payload["event_id"], payload))
        waitlist_service.send_offer_emails(db, offers)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Waitlist expiry job failed: %s", exc)
    finally:
        db.close()
