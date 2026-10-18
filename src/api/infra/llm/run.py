"""``run_llm`` — the single entry point of every LLM call, journaled automatically."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from api.infra.llm.capture import record_llm_call
from api.infra.llm.config import LlmCall
from api.infra.llm.record import LlmCallRecord, llm_retries, llm_usage, output_json
from api.infra.llm.task import LlmTask, OutputT, agent_for, get_model

logger = logging.getLogger(__name__)


async def run_llm(task: LlmTask[OutputT], user_input: str) -> OutputT:
    """Run *task* on *user_input* and return its output.

    The call is recorded (prompt, input, output, tokens, duration, retries) in the active
    ``capture_llm_calls`` — on failure too, with the error, before the exception is re-raised.
    The log line carries no content: prompts and inputs only live in the journal.
    """
    model = get_model(task.tier)
    created_at = datetime.now(UTC)
    t0 = time.monotonic()
    try:
        result = await agent_for(task).run(user_input)
    except Exception as exc:
        _record(task, model, user_input, None, created_at, t0, f"{type(exc).__name__}: {exc}")
        raise
    _record(task, model, user_input, result, created_at, t0, None)
    return result.output


def _record(
    task: LlmTask[Any],
    model: str,
    user_input: str,
    result: Any,
    created_at: datetime,
    t0: float,
    error: str | None,
) -> None:
    """Build the call record, push it to the capture and log a content-free line."""
    duration_ms = round((time.monotonic() - t0) * 1000)
    record = LlmCallRecord(
        task=task.name,
        model=model,
        system_prompt=task.system_prompt,
        input=user_input[: LlmCall.INPUT_LOG_CHARS],
        output=output_json(result.output) if result is not None else None,
        usage=llm_usage(result) if result is not None else None,
        duration_ms=duration_ms,
        created_at=created_at,
        error=error,
        retries=llm_retries(result) if result is not None else [],
    )
    record_llm_call(record)
    tokens = record.usage.total_tokens if record.usage else 0
    status = "ok" if record.ok else f"failed ({error})"
    logger.info("LLM %s [%s] %s in %d ms, %d tokens", task.name, model, status, duration_ms, tokens)
