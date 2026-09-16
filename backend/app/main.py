"""
app/main.py

FastAPI application entry point for the Brillianté Chess Club backend.

Startup lifecycle:
  1. Create any missing DB tables (safety net — Alembic is the primary tool)
  2. Start APScheduler BackgroundScheduler with two jobs:
       • Daily 03:00 AM  — Chess.com rating sync
       • Every 15 min    — Event reminder emails

CORS is configured to allow the static frontend served from Live Server / any local origin.
"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth as auth_router
from app.routers import events as events_router
from app.routers import streams as streams_router
from app.routers import users as users_router
from app.services.scheduler import send_event_reminders, sync_all_chesscom_ratings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── APScheduler instance (module-level so it lives for the app's lifetime) ─────
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info("Creating database tables (if not exist)...")
    Base.metadata.create_all(bind=engine)

    # Job 1: Nightly Chess.com sync — every day at 03:00 AM IST
    scheduler.add_job(
        sync_all_chesscom_ratings,
        trigger=CronTrigger(hour=3, minute=0),
        id="chesscom_sync",
        name="Nightly Chess.com Rating Sync",
        replace_existing=True,
        misfire_grace_time=300,   # allow up to 5-min delay before skipping
    )

    # Job 2: Event reminder emails — every 15 minutes
    scheduler.add_job(
        send_event_reminders,
        trigger=IntervalTrigger(minutes=15),
        id="event_reminders",
        name="Event Reminder Emails (15-min)",
        replace_existing=True,
        misfire_grace_time=60,
    )

    scheduler.start()
    logger.info("APScheduler started with %d jobs.", len(scheduler.get_jobs()))

    yield  # ← application runs here

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("Shutting down APScheduler...")
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped.")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Brillianté Chess Club API",
    description=(
        "Backend for the Adamas University Chess Club website. "
        "Provides auth, events, watch streams, Chess.com leaderboard sync, "
        "and automated email notifications."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if "*" in origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(events_router.router)
app.include_router(streams_router.router)
app.include_router(users_router.router)


# ── Health-check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"], summary="Health check")
def health() -> dict:
    """Returns 200 OK if the API is running."""
    return {"status": "ok", "service": "Brillianté Chess Club API"}
