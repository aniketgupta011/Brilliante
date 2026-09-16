"""
app/database.py

SQLAlchemy 2.0 sync engine, session factory, and FastAPI dependency.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,          # recycle stale connections
    pool_size=10,
    max_overflow=20,
    echo=False,                  # set True to log every SQL statement (debug)
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,      # prevent lazy-load errors after commit
)


# ── Declarative base used by all models ───────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """Yield a DB session, always closing it when the request ends."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
