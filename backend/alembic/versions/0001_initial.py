"""Initial migration — creates users, events, watch_streams tables

Revision ID: 0001
Revises: 
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── userrole enum ─────────────────────────────────────────────────────────
    userrole_enum = sa.Enum("member", "admin", "president", name="userrole")
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            userrole_enum,
            nullable=False,
            server_default="member",
        ),
        sa.Column("chesscom_username", sa.String(100), nullable=True),
        sa.Column("blitz_rating", sa.Integer(), nullable=True),
        sa.Column("rapid_rating", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"])

    # ── events ────────────────────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_ongoing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_events_id", "events", ["id"])

    # ── watch_streams ─────────────────────────────────────────────────────────
    op.create_table(
        "watch_streams",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("youtube_url", sa.String(500), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=False),
        sa.Column(
            "added_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_watch_streams_id", "watch_streams", ["id"])


def downgrade() -> None:
    op.drop_table("watch_streams")
    op.drop_table("events")
    op.drop_table("users")

    # Drop the enum type (PostgreSQL-specific)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
