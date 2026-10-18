"""LLM socle: run_llm + capture, journal persistence, admin screen, retention purge."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.config import Retention
from api.app.llm_calls import LlmSubject, llm_journal, purge_llm_calls
from api.infra.db.models import LlmCallLog, LlmPrompt
from api.infra.llm import LlmTask, agent_for, capture_llm_calls, get_model, run_llm


class Summary(BaseModel):
    title: str
    words: int


SUMMARY = LlmTask(name="summary", system_prompt="Summarize the text.", output_type=Summary)
ECHO = LlmTask(name="echo", system_prompt="Repeat the text.", output_type=str)


@pytest.fixture(autouse=True)
def test_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """pydantic-ai's built-in ``test`` model: deterministic, no network."""
    monkeypatch.setenv("LLM_MODEL_SMALL", "test")


def _boom(messages: list[ModelMessage], info: AgentInfo):
    raise RuntimeError("provider down")


async def test_run_llm_outside_capture_returns_output():
    out = await run_llm(SUMMARY, "some text")

    assert isinstance(out, Summary)


async def test_capture_records_prompt_input_output_and_usage():
    with capture_llm_calls() as calls:
        await run_llm(ECHO, "hello")

    [call] = calls
    assert call.task == "echo"
    assert call.model == "test"
    assert call.system_prompt == "Repeat the text."
    assert call.input == "hello"
    assert isinstance(call.output, str)
    assert call.usage is not None and call.usage.total_tokens > 0
    assert call.ok
    assert call.cost_usd is None  # model not in MODEL_PRICING


async def test_journal_persists_calls_and_dedups_prompts(db_session: AsyncSession):
    with agent_for(SUMMARY).override(
        model=TestModel(custom_output_args={"title": "T", "words": 3})
    ):
        async with llm_journal(db_session, LlmSubject("ticket", "42")):
            await run_llm(SUMMARY, "first")
            await run_llm(SUMMARY, "second")

    rows = (await db_session.execute(select(LlmCallLog).order_by(LlmCallLog.id))).scalars().all()
    assert [r.input for r in rows] == ["first", "second"]
    assert rows[0].output == {"title": "T", "words": 3}
    assert rows[0].input_tokens and rows[0].output_tokens
    assert (rows[0].target_type, rows[0].target_id) == ("ticket", "42")
    prompts = (await db_session.execute(select(func.count()).select_from(LlmPrompt))).scalar_one()
    assert prompts == 1


async def test_failed_call_is_journaled_and_reraised(db_session: AsyncSession):
    with agent_for(ECHO).override(model=FunctionModel(_boom)):
        with pytest.raises(RuntimeError, match="provider down"):
            async with llm_journal(db_session):
                await run_llm(ECHO, "hello")

    row = (await db_session.execute(select(LlmCallLog))).scalar_one()
    assert row.error == "RuntimeError: provider down"
    assert row.output is None


async def test_admin_list_and_detail(admin_client: AsyncClient, db_session: AsyncSession):
    async with llm_journal(db_session):
        await run_llm(ECHO, "hello")

    page = (await admin_client.get("/api/llm-calls")).json()
    assert page["total"] == 1
    item = page["items"][0]
    assert "input" not in item

    detail = (await admin_client.get(f"/api/llm-calls/{item['id']}")).json()
    assert detail["system_prompt"] == "Repeat the text."
    assert detail["input"] == "hello"

    assert (await admin_client.get("/api/llm-calls/tasks")).json() == ["echo"]
    errors = (await admin_client.get("/api/llm-calls", params={"errors_only": True})).json()
    assert errors["total"] == 0


async def test_admin_routes_require_a_session(client: AsyncClient):
    assert (await client.get("/api/llm-calls")).status_code == 401
    assert (await client.get("/api/llm-calls/1")).status_code == 401
    assert (await client.get("/api/llm-calls/tasks")).status_code == 401


async def test_purge_drops_calls_past_retention(db_session: AsyncSession):
    async with llm_journal(db_session):
        await run_llm(ECHO, "old")
        await run_llm(ECHO, "recent")
    old = (
        await db_session.execute(select(LlmCallLog).where(LlmCallLog.input == "old"))
    ).scalar_one()
    old.created_at = datetime.now(UTC) - Retention.LLM_CALLS - timedelta(days=1)
    await db_session.commit()

    assert await purge_llm_calls(db_session) == 1
    remaining = (await db_session.execute(select(LlmCallLog.input))).scalars().all()
    assert remaining == ["recent"]


def test_get_model_fails_clearly_without_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LLM_MODEL_MEDIUM", raising=False)

    with pytest.raises(RuntimeError, match="LLM_MODEL_MEDIUM is not set"):
        get_model("medium")
