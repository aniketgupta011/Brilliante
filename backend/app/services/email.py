"""
app/services/email.py

Email helpers using fastapi-mail.

Two public functions:
  send_new_event_email   — called immediately from the POST /events handler
                           via FastAPI BackgroundTasks (non-blocking)
  send_event_reminder_email — called by the 15-min APScheduler job
"""

import logging
from typing import List

from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

from app.config import settings
from app.models import Event

logger = logging.getLogger(__name__)

_fm: "FastMail | None" = None


def _get_fm() -> FastMail:
    """Lazily create the FastMail client so ConnectionConfig is only validated
    when an email is actually about to be sent — not at import time."""
    global _fm
    if _fm is None:
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        _fm = FastMail(conf)
    return _fm


# ── Templates (inline HTML — no template files needed) ────────────────────────

def _new_event_html(event: Event) -> str:
    return f"""
    <div style="font-family: Inter, system-ui, sans-serif; background:#000; color:#fff;
                max-width:600px; margin:0 auto; padding:40px 32px; border-radius:12px;">
      <h1 style="font-size:28px; font-weight:900; letter-spacing:0.15em; margin:0 0 4px;">
        &#9822; Brillianté
      </h1>
      <p style="color:#737373; font-size:12px; text-transform:uppercase;
                letter-spacing:0.15em; margin:0 0 32px;">Adamas University Chess Club</p>

      <div style="border-top:1px solid #262626; padding-top:24px;">
        <p style="color:#a3a3a3; font-size:11px; text-transform:uppercase;
                  letter-spacing:0.2em; margin:0 0 8px;">New Event</p>
        <h2 style="font-size:22px; font-weight:700; margin:0 0 12px;">{event.title}</h2>
        <p style="color:#a3a3a3; font-size:14px; line-height:1.6; margin:0 0 20px;">
          {event.description or ""}
        </p>
        <p style="font-size:13px; color:#737373;">
          &#128197; <strong style="color:#fff;">
            {event.start_time.strftime("%d %B %Y, %I:%M %p")}
          </strong>
        </p>
      </div>

      <div style="margin-top:32px; padding-top:24px; border-top:1px solid #262626;">
        <p style="color:#525252; font-size:11px; margin:0;">
          You received this because you are a member of Brillianté Chess Club.
        </p>
      </div>
    </div>
    """


def _reminder_html(event: Event) -> str:
    status_text = "is happening NOW" if event.is_ongoing else "starts soon"
    return f"""
    <div style="font-family: Inter, system-ui, sans-serif; background:#000; color:#fff;
                max-width:600px; margin:0 auto; padding:40px 32px; border-radius:12px;">
      <h1 style="font-size:28px; font-weight:900; letter-spacing:0.15em; margin:0 0 4px;">
        &#9822; Brillianté
      </h1>
      <p style="color:#737373; font-size:12px; text-transform:uppercase;
                letter-spacing:0.15em; margin:0 0 32px;">Adamas University Chess Club</p>

      <div style="border-top:1px solid #262626; padding-top:24px;">
        <p style="color:#f59e0b; font-size:11px; text-transform:uppercase;
                  letter-spacing:0.2em; margin:0 0 8px;">&#9200; Reminder</p>
        <h2 style="font-size:22px; font-weight:700; margin:0 0 8px;">{event.title}</h2>
        <p style="color:#a3a3a3; font-size:14px; margin:0 0 16px;">
          This event <strong style="color:#fff;">{status_text}</strong>.
        </p>
        <p style="font-size:13px; color:#737373;">
          &#128197; <strong style="color:#fff;">
            {event.start_time.strftime("%d %B %Y, %I:%M %p")}
          </strong>
        </p>
      </div>

      <div style="margin-top:32px; padding-top:24px; border-top:1px solid #262626;">
        <p style="color:#525252; font-size:11px; margin:0;">
          You received this because you are a member of Brillianté Chess Club.
        </p>
      </div>
    </div>
    """


# ── Public send functions ─────────────────────────────────────────────────────

async def send_new_event_email(event: Event, recipients: List[str]) -> None:
    """
    Send "New Event Added" notification to all *recipients*.
    Called from FastAPI BackgroundTasks so it never blocks the HTTP response.
    """
    if not recipients:
        logger.warning("send_new_event_email: no recipients — skipping.")
        return

    message = MessageSchema(
        subject=f"♟ New Event: {event.title}",
        recipients=recipients,
        body=_new_event_html(event),
        subtype=MessageType.html,
    )

    try:
        await _get_fm().send_message(message)
        logger.info("New-event email sent to %d recipients.", len(recipients))
    except Exception as exc:
        logger.error("Failed to send new-event email: %s", exc)


async def send_event_reminder_email(event: Event, recipients: List[str]) -> None:
    """
    Send event-reminder email.
    Called from the APScheduler asyncio job every 15 minutes.
    """
    if not recipients:
        return

    message = MessageSchema(
        subject=f"⏰ Reminder: {event.title}",
        recipients=recipients,
        body=_reminder_html(event),
        subtype=MessageType.html,
    )

    try:
        await _get_fm().send_message(message)
        logger.info("Reminder email sent for event %d to %d recipients.", event.id, len(recipients))
    except Exception as exc:
        logger.error("Failed to send reminder email for event %d: %s", event.id, exc)
