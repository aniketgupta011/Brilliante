"""
app/schemas.py

Pydantic v2 request/response schemas.
Schemas are deliberately separated from ORM models so the API surface
is fully controlled and never accidentally leaks hashed_password etc.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models import UserRole


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    chesscom_username: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Returned by POST /register — user profile + JWT so the client is
    immediately authenticated without a second round-trip to /login."""
    id: int
    email: EmailStr
    role: UserRole
    chesscom_username: Optional[str]
    blitz_rating: Optional[int]
    rapid_rating: Optional[int]
    created_at: datetime
    access_token: str
    token_type: str = "bearer"

    model_config = {"from_attributes": True}


# ── User ──────────────────────────────────────────────────────────────────────

class UserPublicResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    chesscom_username: Optional[str]
    blitz_rating: Optional[int]
    rapid_rating: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncChesscomRequest(BaseModel):
    chesscom_username: str


class LeaderboardEntry(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    chesscom_username: Optional[str]
    blitz_rating: Optional[int]
    rapid_rating: Optional[int]

    model_config = {"from_attributes": True}


# ── Event ─────────────────────────────────────────────────────────────────────

class EventCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    is_ongoing: bool = False


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    start_time: datetime
    is_ongoing: bool
    email_sent: bool
    created_by: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── WatchStream ───────────────────────────────────────────────────────────────

class StreamCreateRequest(BaseModel):
    title: str
    youtube_url: str

    @field_validator("youtube_url")
    @classmethod
    def must_be_youtube(cls, v: str) -> str:
        if "youtube.com" not in v and "youtu.be" not in v:
            raise ValueError("URL must be a YouTube link.")
        return v


class StreamResponse(BaseModel):
    id: int
    title: str
    youtube_url: str
    thumbnail_url: str
    added_by: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
