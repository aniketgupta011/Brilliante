"""
Alembic environment configuration for Brillianté Chess Club backend.

This file is executed by Alembic to set up the migration context.
It imports our SQLAlchemy models' Base.metadata so that
`alembic revision --autogenerate` can detect schema changes automatically.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Import our app's config and models ────────────────────────────────────────
import sys
import os

# Make sure the `backend/` directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings          # noqa: E402 — must come after sys.path
from app.database import Base            # noqa: E402
import app.models  # noqa: F401, E402   — side-effect: registers all models with Base

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url from our Settings (honours .env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object containing all table definitions
target_metadata = Base.metadata


# ── Run migrations ────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (no live DB connection).
    Generates SQL scripts instead of executing them.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (live DB connection).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
