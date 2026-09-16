"""
app/routers/events.py

Club event endpoints:
  GET    /events         — public; lists all events sorted by start_time
  POST   /events         — admin/president only; creates an event and
                           fires a "New Event" email to all members in the background
  DELETE /events/{id}    — admin/president only; deletes an event
"""

from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Event, User
from app.schemas import EventCreateRequest, EventResponse, MessageResponse
from app.services.email import send_new_event_email

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "",
    response_model=List[EventResponse],
    summary="List all club events (public)",
)
def list_events(db: Session = Depends(get_db)) -> list[Event]:
    """Return all events ordered by start_time ascending."""
    return db.query(Event).order_by(Event.start_time.asc()).all()


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event (admin/president only)",
    dependencies=[Depends(require_admin)],
)
def create_event(
    payload: EventCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Event:
    """
    Create an event and immediately queue a background email blast to all members.
    The HTTP response is returned instantly — the email is sent asynchronously.
    """
    event = Event(
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time,
        is_ongoing=payload.is_ongoing,
        created_by=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Collect all member emails for the notification
    all_emails: list[str] = [u.email for u in db.query(User).all()]

    # Non-blocking — uses FastAPI's BackgroundTasks (runs after response is sent)
    background_tasks.add_task(send_new_event_email, event, all_emails)

    return event


@router.delete(
    "/{event_id}",
    response_model=MessageResponse,
    summary="Delete an event (admin/president only)",
    dependencies=[Depends(require_admin)],
)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a single event by ID."""
    event: Event | None = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found.",
        )

    db.delete(event)
    db.commit()
    return {"message": f"Event '{event.title}' deleted successfully."}
