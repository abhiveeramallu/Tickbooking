from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, bookings, events, organiser, seats, users, venues, waitlist
from app.websocket.manager import manager
from app.workers.hold_expiry import run_hold_expiry_job
from app.workers.waitlist_expiry import run_waitlist_expiry_job


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.add_job(run_hold_expiry_job, "interval", seconds=settings.scheduler_poll_seconds, max_instances=1)
    scheduler.add_job(run_waitlist_expiry_job, "interval", seconds=settings.scheduler_poll_seconds, max_instances=1)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(venues.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(seats.router, prefix=settings.api_prefix)
app.include_router(bookings.router, prefix=settings.api_prefix)
app.include_router(waitlist.router, prefix=settings.api_prefix)
app.include_router(organiser.router, prefix=settings.api_prefix)


@app.get("/health", summary="Health check")
async def health_check() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/events/{event_id}")
async def event_websocket(websocket: WebSocket, event_id: int) -> None:
    await manager.connect(event_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(event_id, websocket)
