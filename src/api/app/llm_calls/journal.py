"""LLM journal: persist the calls captured by ``api.infra.llm`` into ``llm_call`` / ``llm_prompt``.

Usage — wrap the unit of work that calls the LLM (route, background task, script)::

    async with llm_journal(session, LlmSubject("ticket", str(ticket.id))):
        summary = await summarize(ticket.body)  # domain -> run_llm(SUMMARY, ...)

On exit, every captured call is written and committed — failed calls included. If the block
raised, the session is rolled back first (its transaction is dead anyway) and the exception
propagates unchanged. A journal write failure is logged and swallowed: the journal never breaks
nor masks the caller.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.config import Retention
from api.infra.db.models import LlmCallLog, LlmPrompt
from api.infra.llm import LlmCallRecord, capture_llm_calls

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmSubject:
    """What the calls were about — same generic target as notifications."""

    target_type: str
    target_id: str


@asynccontextmanager
async def llm_journal(
    session: AsyncSession, subject: LlmSubject | None = None
) -> AsyncGenerator[list[LlmCallRecord], None]:
    """Capture the LLM calls of the block and persist them on exit (cf. module docstring)."""
    with capture_llm_calls() as calls:
        try:
            yield calls
        except BaseException:
            await session.rollback()
            raise
        finally:
            await _persist_safely(session, calls, subject)


async def _persist_safely(
    session: AsyncSession, calls: list[LlmCallRecord], subject: LlmSubject | None
) -> None:
    """``persist_llm_calls`` that logs instead of raising."""
    try:
        await persist_llm_calls(session, calls, subject)
    except Exception:
        logger.exception("LLM journal write failed (%d calls lost)", len(calls))
        await session.rollback()


async def persist_llm_calls(
    session: AsyncSession, calls: list[LlmCallRecord], subject: LlmSubject | None = None
) -> None:
    """Write the calls and their deduplicated system prompts, then commit."""
    if not calls:
        return
    await _upsert_prompts(session, {c.prompt_hash: c.system_prompt for c in calls})
    session.add_all([_row(c, subject) for c in calls])
    await session.commit()


async def _upsert_prompts(session: AsyncSession, prompts: dict[str, str]) -> None:
    """Insert the prompts not stored yet — select-then-add, dialect-agnostic (SQLite tests)."""
    existing = await session.execute(select(LlmPrompt.hash).where(LlmPrompt.hash.in_(prompts)))
    known = set(existing.scalars())
    session.add_all([LlmPrompt(hash=h, text=t) for h, t in prompts.items() if h not in known])
    await session.flush()


def _row(call: LlmCallRecord, subject: LlmSubject | None) -> LlmCallLog:
    return LlmCallLog(
        created_at=call.created_at,
        task=call.task,
        model=call.model,
        prompt_hash=call.prompt_hash,
        input=call.input,
        output=call.output,
        input_tokens=call.usage.input_tokens if call.usage else None,
        output_tokens=call.usage.output_tokens if call.usage else None,
        cost_usd=call.cost_usd,
        duration_ms=call.duration_ms,
        retries=[asdict(r) for r in call.retries] or None,
        error=call.error,
        target_type=subject.target_type if subject else None,
        target_id=subject.target_id if subject else None,
    )


async def purge_llm_calls(session: AsyncSession) -> int:
    """Delete calls past ``Retention.LLM_CALLS``. Commits itself (background loop).

    Prompts are kept: they are code text, not personal data.
    """
    cutoff = datetime.now(UTC) - Retention.LLM_CALLS
    result = await session.execute(delete(LlmCallLog).where(LlmCallLog.created_at < cutoff))
    await session.commit()
    deleted = cast(CursorResult[Any], result).rowcount or 0
    if deleted:
        logger.info("LLM journal purge: %d calls (cutoff=%s)", deleted, cutoff.date())
    return deleted
