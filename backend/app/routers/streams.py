"""
app/routers/streams.py

YouTube watch-stream endpoints:
  GET  /streams    — public; returns the full stream grid for the frontend
  POST /streams    — admin/president only; accepts a YouTube URL, extracts
                     the video ID via regex, auto-generates thumbnail URL,
                     and saves the record
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import User, WatchStream
from app.schemas import StreamCreateRequest, StreamResponse
from app.utils.youtube import build_thumbnail_url, extract_video_id

router = APIRouter(prefix="/streams", tags=["Watch Streams"])


@router.get(
    "",
    response_model=List[StreamResponse],
    summary="List all watch streams (public)",
)
def list_streams(db: Session = Depends(get_db)) -> list[WatchStream]:
    """Return all streams ordered by newest first."""
    return db.query(WatchStream).order_by(WatchStream.created_at.desc()).all()


@router.post(
    "",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a YouTube stream (admin/president only)",
)
def create_stream(
    payload: StreamCreateRequest,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> WatchStream:
    """
    Extract the 11-character video ID from *youtube_url* using a regex,
    auto-generate the maxresdefault thumbnail URL, and persist the stream.

    Raises 422 if the URL doesn't contain a recognisable video ID.
    """
    video_id = extract_video_id(payload.youtube_url)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not extract a YouTube video ID from the URL. "
                "Supported formats: youtube.com/watch?v=ID, youtu.be/ID, "
                "youtube.com/embed/ID, youtube.com/shorts/ID"
            ),
        )

    thumbnail_url = build_thumbnail_url(video_id)

    stream = WatchStream(
        title=payload.title,
        youtube_url=payload.youtube_url,
        thumbnail_url=thumbnail_url,
        added_by=current_user.id,
    )
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return stream


@router.delete(
    "/{stream_id}",
    summary="Delete a stream (admin/president only)",
)
def delete_stream(
    stream_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> dict:
    """Remove a stream entry from the database."""
    stream: WatchStream | None = db.query(WatchStream).filter(WatchStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found.")

    db.delete(stream)
    db.commit()
    return {"message": f"Stream '{stream.title}' deleted."}
