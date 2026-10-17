"""baseline: admin accounts, sessions, auth journal, notifications

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-17

Aucun compte n'est seedé : le premier admin se crée avec ``make create-admin``
(``scripts/set_admin_password.py --create``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "admin_session",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("admin.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_session_admin_id", "admin_session", ["admin_id"])
    op.create_table(
        "admin_auth_event",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("admin.id"), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("detail", sa.String(255), nullable=True),
    )
    op.create_index("ix_admin_auth_event_occurred_at", "admin_auth_event", ["occurred_at"])
    op.create_table(
        "admin_notification",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipient_admin_id", sa.Integer(), sa.ForeignKey("admin.id"), nullable=False),
        sa.Column("actor_admin_id", sa.Integer(), sa.ForeignKey("admin.id"), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("preview", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_admin_notification_inbox",
        "admin_notification",
        ["recipient_admin_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_notification_inbox", table_name="admin_notification")
    op.drop_table("admin_notification")
    op.drop_index("ix_admin_auth_event_occurred_at", table_name="admin_auth_event")
    op.drop_table("admin_auth_event")
    op.drop_index("ix_admin_session_admin_id", table_name="admin_session")
    op.drop_table("admin_session")
    op.drop_table("admin")
