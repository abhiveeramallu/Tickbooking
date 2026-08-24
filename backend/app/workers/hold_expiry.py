import asyncio
import logging

from app.database.database import SessionLocal
from app.services import seat_service
from app.websocket.manager import manager


logger = logging.getLogger(__name__)


def run_hold_expiry_job() -> None:
    db = SessionLocal()
    try:
        broadcasts = seat_service.release_expired_holds(db)
        for payload in broadcasts:
            asyncio.run(manager.broadcast_event(payload["event_id"], payload))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Hold expiry job failed: %s", exc)
    finally:
        db.close()

