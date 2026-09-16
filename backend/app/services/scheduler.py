"""
app/services/scheduler.py

APScheduler job definitions for the Brillianté backend.

Two scheduled jobs:
  1. sync_all_chesscom_ratings  — daily at 03:00 AM
     Iterates every user with a chesscom_username, fetches the latest
     ratings from Chess.com's PubAPI, and bulk-updates the database.

  2. send_event_reminders       — every 15 minutes
     Finds events starting within the next 24 hours (or already ongoing)
     where email_sent=False, dispatches reminder emails, then flips
     email_sent=True to prevent duplicate sends.

Both jobs are registered inside app/main.py's startup event.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Event, User
from app.services.chesscom import fetch_ratings_sync

logger = logging.getLogger(__name__)


# ── Job 1: Nightly Chess.com sync ─────────────────────────────────────────────

def sync_all_chesscom_ratings() -> None:
    """
    APScheduler job (runs in a thread — synchronous).
    Fetches fresh blitz and rapid ratings for every linked user and saves them.
    """
    logger.info("[Scheduler] Starting nightly Chess.com rating sync...")
    db: Session = SessionLocal()
    try:
        users = (
            db.query(User)
            .filter(User.chesscom_username.isnot(None))
            .all()
        )

        updated = 0
        for user in users:
            try:
                ratings = fetch_ratings_sync(user.chesscom_username)  # type: ignore[arg-type]
                user.blitz_rating = ratings["blitz_rating"]
                user.rapid_rating = ratings["rapid_rating"]
                updated += 1
            except Exception as exc:
                logger.warning(
                    "[Scheduler] Could not fetch ratings for %s: %s",
                    user.chesscom_username, exc,
                )

        db.commit()
        logger.info("[Scheduler] Chess.com sync complete — updated %d users.", updated)

    except Exception as exc:
        db.rollback()
        logger.error("[Scheduler] Nightly sync failed: %s", exc)
    finally:
        db.close()


# ── Job 2: Event reminder emails ──────────────────────────────────────────────

def send_event_reminders() -> None:
    """
    APScheduler job (runs in a thread — uses asyncio.run for the async email send).
    Queries events due within 24 hours or currently ongoing, emails all members,
    and marks email_sent=True so we never double-send.
    """
    logger.info("[Scheduler] Checking for upcoming events to remind about...")
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window = now + timedelta(hours=24)

        # Events starting in the next 24 h OR already marked ongoing, not yet emailed
        events = (
            db.query(Event)
            .filter(
                Event.email_sent.is_(False),
                (Event.start_time <= window) | (Event.is_ongoing.is_(True)),
            )
            .all()
        )

        if not events:
            logger.info("[Scheduler] No upcoming events requiring reminders.")
            return

        # Collect all member emails
        all_emails: list[str] = [u.email for u in db.query(User).all()]

        for event in events:
            try:
                # Run the async email helper inside this synchronous thread
                asyncio.run(_send_reminder(event, all_emails))
                event.email_sent = True
                logger.info("[Scheduler] Reminder sent for event id=%d '%s'.", event.id, event.title)
            except Exception as exc:
                logger.error(
                    "[Scheduler] Reminder failed for event id=%d: %s", event.id, exc
                )

        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("[Scheduler] Event-reminder job failed: %s", exc)
    finally:
        db.close()


async def _send_reminder(event: Event, emails: list[str]) -> None:
    """Internal async helper so we can call the email service from a sync thread."""
    from app.services.email import send_event_reminder_email  # late import avoids circular
    await send_event_reminder_email(event, emails)
