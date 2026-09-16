"""
app/models.py

SQLAlchemy 2.0 ORM models for the Brillianté Chess Club backend.

Tables:
  - users        → User accounts with role-based access
  - events       → Club events with email-sent tracking
  - watch_streams → YouTube stream links with auto-generated thumbnails
"""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    member    = "member"
    admin     = "admin"
    president = "president"


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Club member / admin / president account.
    Passwords are stored as bcrypt hashes — never plaintext.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", create_type=True),
        nullable=False,
        default=UserRole.member,
        server_default=UserRole.member.value,
    )

    # Chess.com integration
    chesscom_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    blitz_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rapid_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    events: Mapped[list["Event"]] = relationship("Event", back_populates="creator")
    streams: Mapped[list["WatchStream"]] = relationship("WatchStream", back_populates="adder")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"


class Event(Base):
    """
    A club event (tournament, workshop, simul, etc.).

    email_sent tracks whether the 15-minute scheduler job has already
    dispatched a reminder so we never double-email members.
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_ongoing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Prevents the reminder scheduler from sending duplicate emails
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # FK to the admin/president who created it
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    creator: Mapped["User | None"] = relationship("User", back_populates="events")

    def __repr__(self) -> str:
        return f"<Event id={self.id} title={self.title!r} start={self.start_time}>"


class WatchStream(Base):
    """
    A YouTube stream/video added by an admin.
    thumbnail_url is auto-generated from the video ID — no manual input needed.
    """
    __tablename__ = "watch_streams"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    youtube_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # FK to the admin/president who added it
    added_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    adder: Mapped["User | None"] = relationship("User", back_populates="streams")

    def __repr__(self) -> str:
        return f"<WatchStream id={self.id} title={self.title!r}>"
