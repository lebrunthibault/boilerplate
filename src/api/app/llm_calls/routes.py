"""Admin read endpoints of the LLM journal: paginated list, then one call in full."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.config import LlmCallsPage
from api.infra.db import get_session
from api.infra.db.models import LlmCallLog, LlmPrompt

router = APIRouter()


class LlmCallSummary(BaseModel):
    """One list line — no prompt, input nor output (they can be large)."""

    id: int
    created_at: datetime
    task: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    duration_ms: int
    error: str | None
    target_type: str | None
    target_id: str | None


class LlmCallPage(BaseModel):
    """Same envelope as ``GET /accounts``."""

    items: list[LlmCallSummary]
    total: int
    page: int
    per_page: int
    pages: int


class LlmCallDetail(LlmCallSummary):
    """One call in full, system prompt rehydrated from ``llm_prompt``."""

    system_prompt: str | None
    input: str
    output: Any
    retries: list[dict[str, Any]] | None


def _summary(row: LlmCallLog) -> dict[str, Any]:
    return {f: getattr(row, f) for f in LlmCallSummary.model_fields}


@router.get("/llm-calls")
async def list_llm_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(LlmCallsPage.SIZE, ge=1, le=LlmCallsPage.SIZE_MAX),
    task: str | None = None,
    errors_only: bool = False,
    session: AsyncSession = Depends(get_session),
) -> LlmCallPage:
    query = select(LlmCallLog)
    if task:
        query = query.where(LlmCallLog.task == task)
    if errors_only:
        query = query.where(LlmCallLog.error.is_not(None))
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await session.execute(
        query.order_by(LlmCallLog.created_at.desc(), LlmCallLog.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return LlmCallPage(
        items=[LlmCallSummary(**_summary(r)) for r in rows.scalars()],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/llm-calls/tasks")
async def list_llm_tasks(session: AsyncSession = Depends(get_session)) -> list[str]:
    """Distinct task names present in the journal — options of the screen's filter."""
    rows = await session.execute(select(LlmCallLog.task).distinct().order_by(LlmCallLog.task))
    return list(rows.scalars())


@router.get("/llm-calls/{call_id}")
async def get_llm_call(call_id: int, session: AsyncSession = Depends(get_session)) -> LlmCallDetail:
    row = await session.get(LlmCallLog, call_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="LLM call not found")
    prompt = await session.get(LlmPrompt, row.prompt_hash)
    return LlmCallDetail(
        **_summary(row),
        system_prompt=prompt.text if prompt else None,
        input=row.input,
        output=row.output,
        retries=row.retries,
    )
