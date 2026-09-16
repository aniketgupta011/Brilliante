"""
app/services/chesscom.py

Thin wrapper around the Chess.com Public API (PubAPI).
Docs: https://www.chess.com/news/view/published-data-api

Rate-limit note: Chess.com asks callers to include a User-Agent and to
not hammer the API. We use httpx with a 10-second timeout and only call
this service during explicit user requests or the nightly scheduler job.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.chess.com/pub"
_HEADERS = {
    "User-Agent": "Brilliante-Chess-Club-Bot/1.0 (contact: chess@university.edu)"
}


async def fetch_ratings(username: str) -> dict[str, Optional[int]]:
    """
    Fetch the latest blitz and rapid ratings for a Chess.com *username*.

    Returns a dict like::

        {"blitz_rating": 1543, "rapid_rating": 1600}

    Both values are None if the player has never played that time control.
    Raises httpx.HTTPStatusError on non-2xx responses (e.g. 404 for bad username).
    """
    url = f"{_BASE}/player/{username}/stats"
    async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()  # propagates 404 → caller handles it
        data = response.json()

    blitz_rating: Optional[int] = (
        data.get("chess_blitz", {}).get("last", {}).get("rating")
    )
    rapid_rating: Optional[int] = (
        data.get("chess_rapid", {}).get("last", {}).get("rating")
    )

    logger.info(
        "Fetched Chess.com ratings for %s — blitz=%s rapid=%s",
        username, blitz_rating, rapid_rating,
    )
    return {"blitz_rating": blitz_rating, "rapid_rating": rapid_rating}


def fetch_ratings_sync(username: str) -> dict[str, Optional[int]]:
    """
    Synchronous version used by the APScheduler background job
    (APScheduler's BackgroundScheduler runs jobs in threads, not an event loop).
    """
    url = f"{_BASE}/player/{username}/stats"
    with httpx.Client(timeout=10.0, headers=_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()

    return {
        "blitz_rating": data.get("chess_blitz", {}).get("last", {}).get("rating"),
        "rapid_rating": data.get("chess_rapid", {}).get("last", {}).get("rating"),
    }
