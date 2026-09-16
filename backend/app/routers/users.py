"""
app/routers/users.py

User-facing endpoints:
  POST /users/sync-chesscom    — authenticated; links a Chess.com username
                                  and immediately fetches + stores ratings
  GET  /users/leaderboard      — public; all users with a Chess.com username,
                                  sorted by blitz_rating descending
  GET  /users/me               — authenticated; returns the caller's own profile
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LeaderboardEntry, MessageResponse, SyncChesscomRequest, UserPublicResponse
from app.services.chesscom import fetch_ratings

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserPublicResponse,
    summary="Get the currently authenticated user's profile",
)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post(
    "/sync-chesscom",
    response_model=UserPublicResponse,
    summary="Link Chess.com account and sync ratings instantly",
)
async def sync_chesscom(
    payload: SyncChesscomRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> User:
    """
    1. Saves the supplied chesscom_username to the user's profile.
    2. Immediately fetches blitz + rapid ratings from Chess.com PubAPI.
    3. Persists the ratings and returns the updated profile.

    Returns 400 if Chess.com can't find the username.
    """
    import httpx  # imported here to keep the module lightweight

    try:
        ratings = await fetch_ratings(payload.chesscom_username)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chess.com user '{payload.chesscom_username}' not found.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chess.com API is currently unavailable. Please try again later.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Chess.com. Check your internet connection.",
        )

    current_user.chesscom_username = payload.chesscom_username
    current_user.blitz_rating = ratings["blitz_rating"]
    current_user.rapid_rating = ratings["rapid_rating"]

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get(
    "/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Public leaderboard ordered by blitz rating",
)
async def leaderboard(db: Session = Depends(get_db)) -> list[User]:
    """
    Returns all users who have linked a Chess.com account,
    fetches live ratings, and sorts by blitz_rating descending.
    Powers the leaders.html page dynamically.
    """
    users = db.query(User).filter(User.chesscom_username.isnot(None)).all()

    if users:
        import asyncio
        async def fetch_for_user(username: str):
            try:
                return username, await fetch_ratings(username)
            except Exception:
                return username, None

        # Fetch concurrently
        results = await asyncio.gather(*(fetch_for_user(u.chesscom_username) for u in users))
        
        # Update sequentially to avoid SQLAlchemy Session concurrency issues
        rating_map = dict(results)
        for u in users:
            r = rating_map.get(u.chesscom_username)
            if r:
                u.blitz_rating = r["blitz_rating"]
                u.rapid_rating = r["rapid_rating"]
                
        db.commit()

    users.sort(key=lambda u: (u.blitz_rating is None, -(u.blitz_rating or 0)))
    return users
