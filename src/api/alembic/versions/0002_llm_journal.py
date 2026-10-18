"""llm journal: deduplicated system prompts + one row per LLM call

Revision ID: 0002_llm_journal
Revises: 0001_baseline
Create Date: 2026-10-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_llm_journal"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_prompt",
        sa.Column("hash", sa.String(64), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "llm_call",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("task", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_hash", sa.String(64), sa.ForeignKey("llm_prompt.hash"), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("retries", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("target_type", sa.String(32), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_llm_call_created_at", "llm_call", [sa.text("created_at DESC")])
    op.create_index("ix_llm_call_task", "llm_call", ["task"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_task", table_name="llm_call")
    op.drop_index("ix_llm_call_created_at", table_name="llm_call")
    op.drop_table("llm_call")
    op.drop_table("llm_prompt")
